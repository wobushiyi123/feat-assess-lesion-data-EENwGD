"""数据处理服务 - Excel导入导出、数据分析

支持两种 Excel 格式：
1. EDC 6-Sheet 格式（临床数据导出）: 靶病灶_基线, 靶病灶, 非靶病灶_基线, 非靶病灶, 新病灶, 肿瘤评估
2. 简化 3-Sheet 格式: 受试者, 靶病灶, 非靶病灶
"""
import io
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import logging

try:
    from openpyxl import load_workbook, Workbook
except ImportError:
    load_workbook = None
    Workbook = None

logger = logging.getLogger(__name__)


def _extract_visit_label(formset_name: str) -> str:
    """从 表单集名称 中提取访视标签

    Examples:
      '肿瘤疗效评估（RECIST1.1）#1（筛选期（给药前28天））' → '筛选期'
      '肿瘤疗效评估（RECIST1.1）#2（第8周±7天）' → '第8周'
    """
    hash_match = re.search(r'#\d+', formset_name)
    if hash_match:
        after_hash = formset_name[hash_match.end():]
        visit_start = after_hash.find('\uff08')  # （
        if visit_start >= 0:
            depth = 0
            visit_end = -1
            for i in range(visit_start, len(after_hash)):
                if after_hash[i] == '\uff08':
                    depth += 1
                elif after_hash[i] == '\uff09':
                    depth -= 1
                    if depth == 0:
                        visit_end = i
                        break
            if visit_end > visit_start:
                inner = after_hash[visit_start + 1:visit_end]
                nested_pos = inner.find('\uff08')
                if nested_pos > 0:
                    return inner[:nested_pos].strip()
                return inner.strip()

    hash_match = re.search(r'#(\d+)', formset_name)
    if hash_match:
        return f"访视{hash_match.group(1)}"
    return formset_name


def _map_ntl_status(assess_result: str) -> str:
    """映射非靶病灶评估结果到标准状态"""
    if assess_result is None or str(assess_result).strip() == '':
        return "持续存在"
    s = str(assess_result).strip()
    if s in ("存在", "稳定", "未见消失"):
        return "持续存在"
    if s in ("消失", "未见", "完全缓解", "未见病灶"):
        return "消失"
    if s in ("明确进展", "进展", "增大", "恶化", "PD"):
        return "进展"
    if "明确进展" in s or "进展" in s:
        return "进展"
    if "消失" in s:
        return "消失"
    return "持续存在"


def _map_human_response(value: str) -> str:
    """将 Excel 中人工评估的中文描述映射为标准 RECIST 代码

    ⚠️ 注意检测顺序：必须先把「非完全缓解/非疾病进展」(Non-CR/Non-PD) 检测出来，
    再检测「完全缓解/CR」。因为「非完全缓解」字符串中包含「完全缓解」子串，
    若顺序相反会被误判为 CR。
    """
    if value is None or str(value).strip() == '':
        return ""
    s = str(value).strip()
    upper = s.upper()
    # 1) Non-CR/Non-PD（否定式，必须最先检测，避免被"完全缓解"子串吞掉）
    if "非完全缓解" in s or "非疾病进展" in s or "NON-CR" in upper or "NON-PD" in upper:
        return "Non-CR/Non-PD"
    # 2) 标准四档 + 不可评估
    if "完全缓解" in s or upper == "CR":
        return "CR"
    if "部分缓解" in s or upper == "PR":
        return "PR"
    if "疾病稳定" in s or upper == "SD":
        return "SD"
    if "疾病进展" in s or upper == "PD":
        return "PD"
    if "不可评估" in s or upper == "NE" or s == "无法评估":
        return "NE"
    # 3) 新病灶
    if s in ("无", "否", "NO", "没有", "No New Lesion"):
        return "No New Lesion"
    if s in ("有", "是", "YES", "New Lesion", "New Lesion → PD"):
        return "New Lesion"
    return s


def _safe_str(val) -> str:
    """安全转字符串"""
    if val is None:
        return ""
    return str(val).strip()


def _safe_float(val) -> float:
    """安全转浮点数"""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    """安全转整数"""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _get_col_val(row, col_map: dict, key: str, default=None):
    """从行数据中按列名安全获取值"""
    idx = col_map.get(key)
    if idx is None or idx >= len(row):
        return default
    return row[idx]


def _norm_header(h):
    """归一化表头：去空白与中英文括号/标点，去掉"只读"等噪声词，转小写，便于容错匹配"""
    s = re.sub(r'[\s（）()\[\]？！、。,\.?!]', '', str(h)).lower()
    return s.replace('只读', '')


def _col_index(headers, *candidates):
    """按候选列名(容错)返回列索引，找不到返回 None"""
    norm = {}
    for i, h in enumerate(headers):
        norm[_norm_header(h)] = i
    for c in candidates:
        idx = norm.get(_norm_header(c))
        if idx is not None:
            return idx
    return None


def _getv(row, headers, *keys, default=None):
    """按候选列名(容错)从行取值"""
    idx = _col_index(headers, *keys)
    if idx is None or idx >= len(row):
        return default
    return row[idx]


# EDC 各 Sheet 的候选名称（兼容命名变体：有无下划线、有无括号等）
EDC_SHEET_VARIANTS = {
    'tl_baseline': ['靶病灶_基线', '靶病灶基线', '靶病灶-基线', 'TargetLesion_Baseline', '靶病灶基线表'],
    'ntl_baseline': ['非靶病灶_基线', '非靶病灶基线', '非靶病灶-基线', 'NonTargetLesion_Baseline', '非靶病灶基线表'],
    'tl': ['靶病灶', '靶病灶随访', 'TargetLesion', '靶病灶表'],
    'ntl': ['非靶病灶', '非靶病灶随访', 'NonTargetLesion', '非靶病灶表'],
    'nl': ['新病灶', 'NewLesion', '新病灶表'],
    'summary': ['肿瘤评估（RECIST1.1）', '肿瘤评估(RECIST1.1)', '肿瘤评估RECIST1.1', '肿瘤评估', '疗效评估'],
}


def _resolve_sheet(wb, key):
    """按候选名称解析 sheet，找不到返回 None"""
    for name in EDC_SHEET_VARIANTS.get(key, []):
        if name in wb.sheetnames:
            return wb[name]
    return None



class DataProcessor:
    """数据处理器"""

    # EDC 格式 Sheet 名称
    EDC_SHEETS = ['靶病灶_基线', '靶病灶', '非靶病灶_基线', '非靶病灶', '新病灶', '肿瘤评估（RECIST1.1）']

    @staticmethod
    def _detect_format(sheet_names: List[str]) -> str:
        """检测 Excel 格式: 'edc' 或 'simple'（兼容表名变体）"""
        present = set(sheet_names)
        edc_count = 0
        for variants in EDC_SHEET_VARIANTS.values():
            if any(v in present for v in variants):
                edc_count += 1
        return 'edc' if edc_count >= 4 else 'simple'

    @staticmethod
    def parse_edc_format(file_content: bytes) -> Dict[str, Any]:
        """
        解析 EDC 6-Sheet 格式 Excel

        Returns:
            {
                "format": "edc",
                "subjects": [...],           # 受试者信息（去重）
                "subject_timepoints": {      # 每受试者每时间点的评估数据
                    "subject_id": [{
                        "timepoint": "筛选期",
                        "formset_num": 1,
                        "assessment_date": "",
                        "target_lesions": [...],
                        "non_target_lesions": [...],
                        "has_new_lesion": False,
                        "new_lesion_details": [...],
                        "tumor_marker_normal": True,  # EDC中通常通过非靶病灶推断
                    }, ...]
                },
                "parse_errors": [],
            }
        """
        wb = load_workbook(io.BytesIO(file_content), data_only=True)
        sheet_names = wb.sheetnames
        parse_errors = []

        # ===== 1. 解析 靶病灶_基线 =====
        tl_baseline_by_subject = {}
        ws = _resolve_sheet(wb, 'tl_baseline')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue

                has_tl = _safe_str(_getv(row, headers, '是否存在靶病灶')) == '是'

                if sid not in tl_baseline_by_subject:
                    tl_baseline_by_subject[sid] = {
                        'has_tl': has_tl,
                        'lesions': [],
                    }

                lesion_id = _safe_str(_getv(row, headers, '靶病灶编号'))
                organ = _safe_str(_getv(row, headers, '病灶所在器官'))
                organ_detail = _safe_str(_getv(row, headers, '病灶所在器官具体描述'))
                diameter = _safe_float(_getv(row, headers, '最长直径（非淋巴结）/最短直径（淋巴结）', '所有靶病灶直径和', '靶病灶直径和', '最长直径', '最长直径(mm)', '基线最长径(mm)', '最长径', '基线最长径', '直径和', '靶病灶直径', '病灶直径'))

                # 只要有「存在靶病灶」标志或填写了器官/直径，就录入该病灶（提高容错，避免模板列名差异导致整行丢失）
                if has_tl or organ or diameter:
                    tl_baseline_by_subject[sid]['lesions'].append({
                        'name': f"{organ} - {organ_detail}" if organ_detail else organ,
                        'location': organ,
                        'description': organ_detail,
                        'lesion_id': lesion_id,
                        'baseline_size': diameter,
                        'current_size': diameter,  # 基线: current = baseline
                        'sum_diameter': _safe_float(_getv(row, headers, '所有靶病灶直径和', '靶病灶直径和')),
                        'size_unit': _safe_str(_getv(row, headers, '所有靶病灶直径和（只读）(Unit)', '所有靶病灶直径和(unit)', '最长直径（非淋巴结）/最短直径（淋巴结）(unit)', '直径单位', 'unit')) or 'mm',
                        'is_checked': has_tl,
                        'exam_date': _safe_str(_getv(row, headers, '检查日期')),
                        'exam_method': _safe_str(_getv(row, headers, '检查方法')),
                        'other_exam_method': _safe_str(_getv(row, headers, '其他检查方法')),
                        'is_split_fused': _safe_str(_getv(row, headers, '病灶是否发生了分裂或融合？', '是否发生分裂或融合', '分裂融合')),
                        'split_fuse_detail': _safe_str(_getv(row, headers, '如分裂或融合，请详述', '分裂融合详述', '详述')),
                        'unmeasurable_reason': _safe_str(_getv(row, headers, '无法精确测量的原因', '无法测量原因')),
                        'notes': f"EDC编号: {lesion_id}",
                    })

        # ===== 2. 解析 非靶病灶_基线 =====
        ntl_baseline_by_subject = {}
        ws = _resolve_sheet(wb, 'ntl_baseline')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue

                has_ntl = _safe_str(_getv(row, headers, '是否存在非靶病灶')) == '是'

                if sid not in ntl_baseline_by_subject:
                    ntl_baseline_by_subject[sid] = {
                        'has_ntl': has_ntl,
                        'lesions': [],
                    }

                if has_ntl:
                    lesion_id = _safe_str(_getv(row, headers, '非靶病灶编号'))
                    organ = _safe_str(_getv(row, headers, '病灶所在器官'))
                    organ_detail = _safe_str(_getv(row, headers, '病灶所在器官具体描述'))

                    ntl_baseline_by_subject[sid]['lesions'].append({
                        'name': f"{organ} - {organ_detail}" if organ_detail else organ,
                        'location': organ,
                        'description': organ_detail,
                        'lesion_id': lesion_id,
                        'status': '持续存在',  # 基线默认为存在
                        'is_checked': has_ntl,  # 基线是否进行了非靶病灶检查
                        'exam_date': _safe_str(_getv(row, headers, '检查日期')),
                        'exam_method': _safe_str(_getv(row, headers, '检查方法')),
                        'notes': f"EDC编号: {lesion_id}",
                    })

        # ===== 3. 收集所有受试者 ID =====
        all_ids = set()
        all_ids.update(tl_baseline_by_subject.keys())
        all_ids.update(ntl_baseline_by_subject.keys())

        # 从其他 Sheet 也收集
        for key in ['tl', 'ntl', 'nl']:
            ws = _resolve_sheet(wb, key)
            if ws is not None:
                headers = [_safe_str(cell.value) for cell in ws[1]]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                    if sid:
                        all_ids.add(sid)

        # ===== 4. 按 (subject_id, formset_num) 组织随访数据 =====
        # 靶病灶随访
        tl_followup = defaultdict(lambda: defaultdict(list))
        ws = _resolve_sheet(wb, 'tl')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue
                fn = _safe_int(_getv(row, headers, '表单集记录号'))

                has_tl_check = _safe_str(_getv(row, headers, '是否进行了靶病灶检查')) == '是'
                formset_name = _safe_str(_getv(row, headers, '表单集名称'))
                visit_label = _extract_visit_label(formset_name) if formset_name else f"访视{fn}"

                lesion_id = _safe_str(_getv(row, headers, '靶病灶编号'))
                organ = _safe_str(_getv(row, headers, '病灶所在器官'))
                organ_detail = _safe_str(_getv(row, headers, '病灶所在器官具体描述'))
                diameter = _safe_float(_getv(row, headers, '最长直径（非淋巴结）/最短直径（淋巴结）', '所有靶病灶直径和', '靶病灶直径和', '最长直径', '最长直径(mm)', '当前最长径(mm)', '当前最长径', '最长径', '直径和', '靶病灶直径', '病灶直径'))

                tp_key = (sid, fn)
                if not tl_followup[tp_key].get('_meta'):
                    tl_followup[tp_key]['_meta'] = {
                        'timepoint': visit_label,
                        'formset_num': fn,
                        'has_tl_check': has_tl_check,
                        'formset_name': formset_name,
                    }
                    tl_followup[tp_key]['_lesions'] = []

                # 只要有器官或直径即录入该病灶（提高容错，避免模板列名/标志差异导致整行丢失）
                if organ or diameter:
                    tl_followup[tp_key]['_lesions'].append({
                        'name': f"{organ} - {organ_detail}" if organ_detail else organ,
                        'location': organ,
                        'description': organ_detail,
                        'lesion_id': lesion_id,
                        'current_size': diameter,
                        'sum_diameter': _safe_float(_getv(row, headers, '所有靶病灶直径和', '靶病灶直径和')),
                        'size_unit': _safe_str(_getv(row, headers, '所有靶病灶直径和（只读）(Unit)', '所有靶病灶直径和(unit)', '最长直径（非淋巴结）/最短直径（淋巴结）(unit)', '直径单位', 'unit')) or 'mm',
                        # 当前(随访)检查信息
                        'current_is_checked': has_tl_check,
                        'current_exam_date': _safe_str(_getv(row, headers, '检查日期')),
                        'current_exam_method': _safe_str(_getv(row, headers, '检查方法')),
                        'current_other_exam_method': _safe_str(_getv(row, headers, '其他检查方法')),
                        'current_is_split_fused': _safe_str(_getv(row, headers, '病灶是否发生了分裂或融合？', '是否发生分裂或融合', '分裂融合')),
                        'current_split_fuse_detail': _safe_str(_getv(row, headers, '如分裂或融合，请详述', '分裂融合详述', '详述')),
                        'notes': f"EDC编号: {lesion_id}",
                    })

        # 非靶病灶随访
        ntl_followup = defaultdict(lambda: defaultdict(list))
        ws = _resolve_sheet(wb, 'ntl')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue
                fn = _safe_int(_getv(row, headers, '表单集记录号'))

                has_ntl_check = _safe_str(_getv(row, headers, '是否进行了非靶病灶检查')) == '是'
                formset_name = _safe_str(_getv(row, headers, '表单集名称'))
                visit_label = _extract_visit_label(formset_name) if formset_name else f"访视{fn}"

                lesion_id = _safe_str(_getv(row, headers, '非靶病灶编号'))
                organ = _safe_str(_getv(row, headers, '病灶所在器官'))
                organ_detail = _safe_str(_getv(row, headers, '病灶所在器官具体描述'))
                assess_result = _safe_str(_getv(row, headers, '评估结果'))

                tp_key = (sid, fn)
                if not ntl_followup[tp_key].get('_meta'):
                    ntl_followup[tp_key]['_meta'] = {
                        'timepoint': visit_label,
                        'formset_num': fn,
                        'has_ntl_check': has_ntl_check,
                        'formset_name': formset_name,
                    }
                    ntl_followup[tp_key]['_lesions'] = []

                if organ:
                    status = _map_ntl_status(assess_result)
                    ntl_followup[tp_key]['_lesions'].append({
                        'name': f"{organ} - {organ_detail}" if organ_detail else organ,
                        'location': organ,
                        'description': organ_detail,
                        'lesion_id': lesion_id,
                        'status': status,
                        'current_is_checked': has_ntl_check,  # 当前是否进行了非靶病灶检查
                        'current_exam_date': _safe_str(_getv(row, headers, '检查日期')),
                        'current_exam_method': _safe_str(_getv(row, headers, '检查方法')),
                        'notes': f"EDC编号: {lesion_id}",
                    })

        # 新病灶
        nl_followup = defaultdict(lambda: defaultdict(list))
        ws = _resolve_sheet(wb, 'nl')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue
                fn = _safe_int(_getv(row, headers, '表单集记录号'))
                has_nl = _safe_str(_getv(row, headers, '是否有新病灶检出')) == '是'
                formset_name = _safe_str(_getv(row, headers, '表单集名称'))
                visit_label = _extract_visit_label(formset_name) if formset_name else f"访视{fn}"

                lesion_id = _safe_str(_getv(row, headers, '新病灶编号'))
                organ = _safe_str(_getv(row, headers, '病灶所在器官'))
                organ_detail = _safe_str(_getv(row, headers, '病灶所在器官具体描述'))

                tp_key = (sid, fn)
                if not nl_followup[tp_key].get('_meta'):
                    nl_followup[tp_key]['_meta'] = {
                        'timepoint': visit_label,
                        'formset_num': fn,
                        'has_new_lesion': has_nl,
                        'new_lesions': [],
                    }

                nl_followup[tp_key]['has_new_lesion'] = has_nl or bool(organ) or nl_followup[tp_key].get('has_new_lesion', False)
                if organ:
                    nl_followup[tp_key].setdefault('new_lesions', []).append({
                        'name': f"{organ} - {organ_detail}" if organ_detail else organ,
                        'location': organ,
                        'description': organ_detail,
                        'lesion_id': lesion_id,
                        'exam_date': _safe_str(_getv(row, headers, '检查日期')),
                        'exam_method': _safe_str(_getv(row, headers, '检查方法')),
                        'other_exam_method': _safe_str(_getv(row, headers, '其他检查方法')),
                        'notes': f"EDC编号: {lesion_id}",
                    })

        # ===== 6. 解析人工评估（Sheet 6: 肿瘤评估（RECIST1.1）） =====
        human_assessments = defaultdict(dict)
        ws = _resolve_sheet(wb, 'summary')
        if ws is not None:
            headers = [_safe_str(cell.value) for cell in ws[1]]

            for row in ws.iter_rows(min_row=2, values_only=True):
                sid = _safe_str(_getv(row, headers, '受试者编号', row[1] if len(row) > 1 else ''))
                if not sid:
                    continue
                fn = _safe_int(_getv(row, headers, '表单集记录号'))
                formset_name = _safe_str(_getv(row, headers, '表单集名称'))
                visit_label = _extract_visit_label(formset_name) if formset_name else f"访视{fn}"

                tl_human = _map_human_response(_getv(row, headers, '靶病灶评估'))
                ntl_human = _map_human_response(_getv(row, headers, '非靶病灶评估'))
                nl_human = _map_human_response(_getv(row, headers, '新病灶'))
                overall_human = _map_human_response(_getv(row, headers, '总体疗效评估'))

                human_assessments[sid][fn] = {
                    'timepoint': visit_label,
                    'visit_name': formset_name or '',  # 保留完整 EDC 原始访视名称
                    'formset_num': fn,
                    'tl_human': tl_human,
                    'ntl_human': ntl_human,
                    'nl_human': nl_human,
                    'overall_human': overall_human,
                }

        # ===== 7. 组装每个受试者每时间点的完整数据 =====
        subject_timepoints = {}
        for sid in all_ids:
            # 收集该受试者所有时间点
            all_timepoint_keys = set()
            all_timepoint_keys.update(k[1] for k in tl_followup if k[0] == sid)
            all_timepoint_keys.update(k[1] for k in ntl_followup if k[0] == sid)
            all_timepoint_keys.update(k[1] for k in nl_followup if k[0] == sid)

            tl_baseline = tl_baseline_by_subject.get(sid, {'has_tl': False, 'lesions': []})
            ntl_baseline = ntl_baseline_by_subject.get(sid, {'has_ntl': False, 'lesions': []})

            timepoints = []

            for fn in sorted(all_timepoint_keys):
                tl_data = tl_followup.get((sid, fn), {})
                ntl_data = ntl_followup.get((sid, fn), {})
                nl_data = nl_followup.get((sid, fn), {})

                tp_label = (
                    tl_data.get('_meta', {}).get('timepoint', '')
                    or ntl_data.get('_meta', {}).get('timepoint', '')
                    or nl_data.get('_meta', {}).get('timepoint', '')
                    or f"访视{fn}"
                )

                # 靶病灶：SLD = 本周期所有靶病灶「最长直径(非淋巴结)/最短直径(淋巴结)」[列16] 之和，
                # 与病灶编号无关。故以「本次访视实际测量的病灶」为基准遍历，基线径线按
                # 病灶编号(优先)/名称(兜底)匹配回填——避免"器官具体描述写法不同"导致对不上、
                # 当期径线退回基线、SLD 算错。基线存在但本期未测(病灶消失/resolved)的病灶不计入当期 SLD。
                bl_by_id = {bl.get('lesion_id'): bl for bl in tl_baseline.get('lesions', [])}
                bl_by_name = {bl.get('name', ''): bl for bl in tl_baseline.get('lesions', []) if bl.get('name')}
                target_lesions = []
                for c in tl_data.get('_lesions', []):
                    bl = bl_by_id.get(c.get('lesion_id')) or bl_by_name.get(c.get('name', ''))
                    target_lesions.append({
                        'name': c.get('name', ''),
                        'location': c.get('location', ''),
                        'description': c.get('description', '') or (bl.get('description', '') if bl else ''),
                        'lesion_id': c.get('lesion_id', '') or (bl.get('lesion_id', '') if bl else ''),
                        'baseline_size': bl.get('baseline_size', 0) if bl else 0.0,
                        'current_size': c.get('current_size', 0),
                        'size_unit': c.get('size_unit') or (bl.get('size_unit', 'mm') if bl else 'mm'),
                        'sum_diameter': c.get('sum_diameter', 0),
                        # 基线检查信息
                        'is_checked': (bl.get('is_checked', True) if bl else True),
                        'exam_date': bl.get('exam_date') if bl else None,
                        'exam_method': bl.get('exam_method') if bl else None,
                        'other_exam_method': bl.get('other_exam_method') if bl else None,
                        'is_split_fused': bl.get('is_split_fused') if bl else None,
                        'split_fuse_detail': bl.get('split_fuse_detail') if bl else None,
                        'unmeasurable_reason': bl.get('unmeasurable_reason') if bl else None,
                        # 当前(随访)检查信息
                        'current_is_checked': c.get('current_is_checked'),
                        'current_exam_date': c.get('current_exam_date'),
                        'current_exam_method': c.get('current_exam_method'),
                        'current_other_exam_method': c.get('current_other_exam_method'),
                        'current_is_split_fused': c.get('current_is_split_fused'),
                        'current_split_fuse_detail': c.get('current_split_fuse_detail'),
                        'notes': c.get('notes', ''),
                    })

                # 非靶病灶：同样以本次访视实际测量的病灶为基准，基线状态按编号/名称匹配回填
                nbl_by_id = {bl.get('lesion_id'): bl for bl in ntl_baseline.get('lesions', [])}
                nbl_by_name = {bl.get('name', ''): bl for bl in ntl_baseline.get('lesions', []) if bl.get('name')}
                non_target_lesions = []
                for c in ntl_data.get('_lesions', []):
                    bl = nbl_by_id.get(c.get('lesion_id')) or nbl_by_name.get(c.get('name', ''))
                    non_target_lesions.append({
                        'name': c.get('name', ''),
                        'location': c.get('location', ''),
                        'description': c.get('description', '') or (bl.get('description', '') if bl else ''),
                        'lesion_id': c.get('lesion_id', '') or (bl.get('lesion_id', '') if bl else ''),
                        'baseline_status': bl.get('status', '持续存在') if bl else '持续存在',
                        'status': c.get('status', '持续存在'),
                        # 基线检查信息
                        'baseline_is_checked': (bl.get('is_checked', True) if bl else True),
                        'exam_date': bl.get('exam_date') if bl else None,
                        'exam_method': bl.get('exam_method') if bl else None,
                        # 当前(随访)检查信息
                        'current_is_checked': c.get('current_is_checked'),
                        'current_exam_date': c.get('current_exam_date'),
                        'current_exam_method': c.get('current_exam_method'),
                        'notes': c.get('notes', ''),
                    })

                has_new = nl_data.get('has_new_lesion', False)

                # 人工评估数据（如存在）
                human = human_assessments.get(sid, {}).get(fn, {})

                # 从当前周期病灶中提取实际检测日期（优先取靶病灶的随访检查日期）
                _tp_exam_date = None
                for _tl in target_lesions:
                    if _tl.get('current_exam_date'):
                        _tp_exam_date = _tl['current_exam_date']
                        break
                if not _tp_exam_date:
                    for _ntl in non_target_lesions:
                        if _ntl.get('current_exam_date'):
                            _tp_exam_date = _ntl['current_exam_date']
                            break
                if not _tp_exam_date and nl_data.get('new_lesions'):
                    for _nl in nl_data['new_lesions']:
                        if _nl.get('exam_date'):
                            _tp_exam_date = _nl['exam_date']
                            break

                timepoints.append({
                    'timepoint': tp_label,
                    'visit_name': human.get('visit_name', ''),  # EDC 原始访视名称（来自 Sheet6 表单集名称）
                    'assessment_date': _tp_exam_date or '',      # Excel 中该周期的实际检测日期
                    'formset_num': fn,
                    'target_lesions': target_lesions,
                    'non_target_lesions': non_target_lesions,
                    'has_new_lesion': has_new,
                    'new_lesion_details': nl_data.get('new_lesions', []),
                    'tumor_marker_normal': True,  # EDC 默认，可按需从 Sheet6 推断
                    'human_assessment': human,
                })

            subject_timepoints[sid] = {
                'has_tl_baseline': tl_baseline.get('has_tl', False),
                'has_ntl_baseline': ntl_baseline.get('has_ntl', False),
                'timepoints': timepoints,
            }

        # ===== 6. 构建简化的 subjects 列表 =====
        subjects = []
        for sid in sorted(all_ids):
            tp_info = subject_timepoints.get(sid, {})
            subjects.append({
                'subject_id': sid,
                'name': sid,  # EDC 中通常以编号作为标识
                'has_tl': tp_info.get('has_tl_baseline', False),
                'has_ntl': tp_info.get('has_ntl_baseline', False),
            })

        return {
            'format': 'edc',
            'subjects': subjects,
            'subject_timepoints': subject_timepoints,
            'human_assessments': human_assessments,
            'parse_errors': parse_errors,
        }

    @staticmethod
    def parse_excel(file_content: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析 Excel 文件（自动检测格式）

        支持:
        - EDC 6-Sheet 格式（临床数据导出）
        - 简化 3-Sheet 格式（受试者、靶病灶、非靶病灶）

        为保持向后兼容，返回统一结构:
        {
            "format": "edc" | "simple",
            "subjects": [...],
            "target_lesions": [...],      # simple 格式
            "non_target_lesions": [...],  # simple 格式
            "subject_timepoints": {...},  # EDC 格式
            "parse_errors": [...],
        }
        """
        if load_workbook is None:
            raise ValueError("openpyxl not installed")

        try:
            wb = load_workbook(io.BytesIO(file_content), data_only=True)
            sheet_names = wb.sheetnames

            # 检测格式
            fmt = DataProcessor._detect_format(sheet_names)

            if fmt == 'edc':
                # 使用 EDC 解析器
                return DataProcessor.parse_edc_format(file_content)

            # === 简化 3-Sheet 格式（原逻辑） ===
            result = {
                "format": "simple",
                "subjects": [],
                "target_lesions": [],
                "non_target_lesions": [],
                "subject_timepoints": {},
                "parse_errors": [],
            }

            sheet_map = {
                "subjects": ["受试者", "Sheet1", "subjects"],
                "target_lesions": ["靶病灶", "Sheet2", "target_lesions"],
                "non_target_lesions": ["非靶病灶", "Sheet3", "non_target_lesions"]
            }

            for key, names in sheet_map.items():
                sheet = None
                for name in names:
                    if name in sheet_names:
                        sheet = wb[name]
                        break
                if sheet is None and sheet_names:
                    idx = list(sheet_map.keys()).index(key)
                    if idx < len(sheet_names):
                        sheet = wb[sheet_names[idx]]
                if sheet is None:
                    continue

                rows = list(sheet.iter_rows(values_only=True))
                if not rows:
                    continue

                headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
                for row in rows[1:]:
                    record = {}
                    for i, val in enumerate(row):
                        if i < len(headers):
                            if val is None:
                                record[headers[i]] = ""
                            elif hasattr(val, 'isoformat'):
                                record[headers[i]] = val.isoformat()
                            else:
                                record[headers[i]] = val
                    result[key].append(record)

            return result
        except Exception as e:
            logger.error(f"Excel解析失败: {e}")
            raise ValueError(f"Excel文件解析失败: {str(e)}")

    @staticmethod
    def export_to_excel(subjects: List[Dict], assessments: List[Dict]) -> bytes:
        """
        导出数据到Excel

        包含:
        - 受试者列表
        - 评估结果
        - 统计摘要
        """
        if Workbook is None:
            raise ValueError("openpyxl not installed")

        output = io.BytesIO()
        wb = Workbook()

        ws_subject = wb.active
        ws_subject.title = "受试者"
        if subjects:
            headers = list(subjects[0].keys())
            ws_subject.append(headers)
            for row in subjects:
                ws_subject.append([row.get(h, "") for h in headers])

        ws_assess = wb.create_sheet("评估结果")
        if assessments:
            headers = list(assessments[0].keys())
            ws_assess.append(headers)
            for row in assessments:
                ws_assess.append([row.get(h, "") for h in headers])

        ws_summary = wb.create_sheet("统计摘要")
        if assessments:
            status_counts = {}
            for a in assessments:
                s = a.get("overall_status", "未知")
                status_counts[s] = status_counts.get(s, 0) + 1
            ws_summary.append(["评估状态", "数量"])
            for status, count in status_counts.items():
                ws_summary.append([status, count])

        wb.save(output)
        return output.getvalue()

    @staticmethod
    def validate_subject_data(data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证受试者数据"""
        if not data.get("subject_id"):
            return False, "受试者ID不能为空"
        if not data.get("name"):
            return False, "姓名不能为空"
        return True, ""

    @staticmethod
    def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据 - 去除空值、标准化"""
        cleaned = {}
        for key, value in data.items():
            if value is None or value == "" or (isinstance(value, float) and value != value):
                cleaned[key] = None
            elif isinstance(value, str):
                cleaned[key] = value.strip()
            else:
                cleaned[key] = value
        return cleaned
