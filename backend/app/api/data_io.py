"""数据导入导出API"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from typing import Dict, Any
import io
import traceback as tb
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.database import User, Subject, Assessment, TargetLesion, NonTargetLesion, NewLesion, ImportBatch
from app.services.data_processor import DataProcessor
from app.services.recist_engine import RecistEngine
from app.services.intelligent_analyzer import IntelligentAnalyzer

router = APIRouter(prefix="/api/data", tags=["数据导入导出"])


def _safe_str(value) -> str:
    """安全地转换为字符串，None 返回空字符串"""
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value) -> int | None:
    """安全地转换为 int，空值返回 None，区别于 int(0) or None 会把 0 变成 None"""
    if value is None or value == "" or value == "None":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> float:
    """安全地转换为 float"""
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _safe_bool(value) -> bool | None:
    """安全地转换为 bool，空值返回 None（区别于 bool 默认值）"""
    if value is None or value == "" or value == "None":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in ("true", "1", "是", "yes", "y")


@router.post("/import")
async def import_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """导入Excel数据并按 RECIST 1.1 重新计算评估结果

    支持两种格式:
    - EDC 6-Sheet 格式: 多时间点数据，自动创建多条 Assessment，追踪 nadir
    - 简化 3-Sheet 格式: 单次评估数据（向后兼容）
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持Excel文件")

    content = await file.read()

    try:
        parsed_data = DataProcessor.parse_excel(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    fmt = parsed_data.get("format", "simple")

    try:
        # ===== 0. 创建导入批次 =====
    batch = ImportBatch(
        user_id=current_user.id,
        filename=file.filename or "unknown.xlsx",
        import_time=datetime.now(),
        total_assessments=0,
        subjects_count=0
    )
    db.add(batch)
    db.flush()

    # ===== 1. 导入/更新受试者 =====
    subjects_created = 0
    subjects_map: Dict[str, int] = {}

    if fmt == "edc":
        # EDC 格式: subjects 来自解析结果
        for subj in parsed_data.get("subjects", []):
            subject_id = _safe_str(subj.get("subject_id") or subj.get("受试者编号"))
            name = _safe_str(subj.get("name") or subject_id)
            if not subject_id:
                continue

            existing = db.query(Subject).filter(
                Subject.subject_id == subject_id,
                Subject.user_id == current_user.id
            ).first()
            if existing:
                if name:
                    existing.name = name
                subjects_map[subject_id] = existing.id
            else:
                subject = Subject(
                    subject_id=subject_id,
                    name=name,
                    gender="",
                    age=None,
                    diagnosis="",
                    user_id=current_user.id,
                )
                db.add(subject)
                db.flush()
                subjects_map[subject_id] = subject.id
                subjects_created += 1
    else:
        # 简化格式
        for row in parsed_data["subjects"]:
            cleaned = DataProcessor.clean_data(row)
            subject_id = cleaned.get("subject_id") or cleaned.get("受试者ID")
            name = cleaned.get("name") or cleaned.get("姓名")

            if not subject_id or not name:
                continue

            subject_id = str(subject_id).strip()
            existing = db.query(Subject).filter(
                Subject.subject_id == subject_id,
                Subject.user_id == current_user.id
            ).first()
            if existing:
                existing.name = str(name)
                existing.gender = str(cleaned.get("gender") or cleaned.get("性别") or "")
                existing.age = _safe_int(cleaned.get("age") or cleaned.get("年龄"))
                existing.diagnosis = str(cleaned.get("diagnosis") or cleaned.get("诊断") or "")
                subjects_map[subject_id] = existing.id
            else:
                subject = Subject(
                    subject_id=subject_id,
                    name=str(name),
                    gender=str(cleaned.get("gender") or cleaned.get("性别") or ""),
                    age=_safe_int(cleaned.get("age") or cleaned.get("年龄")),
                    diagnosis=str(cleaned.get("diagnosis") or cleaned.get("诊断") or ""),
                    user_id=current_user.id,
                )
                db.add(subject)
                db.flush()
                subjects_map[subject_id] = subject.id
                subjects_created += 1

    # ===== 2. 按格式处理评估数据 =====
    assessments_created = 0
    assessments_updated = 0
    total_assessments = 0

    if fmt == "edc":
        # === EDC 多时间点导入 ===
        subject_timepoints = parsed_data.get("subject_timepoints", {})

        for subj_id, tp_info in subject_timepoints.items():
            subject_db_id = subjects_map.get(subj_id)
            if not subject_db_id:
                continue

            timepoints = tp_info.get("timepoints", [])
            has_tl = tp_info.get("has_tl_baseline", False)
            has_ntl = tp_info.get("has_ntl_baseline", False)

            # 追踪该受试者的 nadir SLD
            baseline_sld = 0.0
            nadir_sld = None

            for cycle, tp in enumerate(timepoints, start=1):
                target_lesions_raw = tp.get("target_lesions", [])
                non_target_lesions_raw = tp.get("non_target_lesions", [])
                has_new_lesion = tp.get("has_new_lesion", False)
                tumor_marker_normal = tp.get("tumor_marker_normal", True)
                timepoint_label = tp.get("timepoint", f"周期{cycle}")
                visit_name = tp.get("visit_name", "")  # EDC 原始访视名称
                human = tp.get("human_assessment", {})

                # 快照隔离：每次导入都为本批次创建「独立」的评估记录。
                # 仅当本批次内已存在相同(受试者, 周期)时才原地更新，
                # 绝不复用/搬动其它批次的评估，避免旧批次数据被抽空。
                existing = db.query(Assessment).filter(
                    Assessment.subject_id == subject_db_id,
                    Assessment.cycle_number == cycle,
                    Assessment.batch_id == batch.id
                ).first()

                # assessment_date 取自 Excel 该周期的实际检查日期，而非导入时刻
                _tp_date_str = tp.get("assessment_date", "")
                _parsed_date = None
                if _tp_date_str:
                    try:
                        _parsed_date = datetime.fromisoformat(_tp_date_str)
                    except (ValueError, TypeError):
                        pass
                if _parsed_date is None:
                    _parsed_date = datetime.now(timezone.utc)

                if existing:
                    # 同批次内重复导入：先清空旧病灶，再重写，避免病灶重复累积
                    db.query(TargetLesion).filter(TargetLesion.assessment_id == existing.id).delete()
                    db.query(NonTargetLesion).filter(NonTargetLesion.assessment_id == existing.id).delete()
                    db.query(NewLesion).filter(NewLesion.assessment_id == existing.id).delete()
                    assessment = existing
                    assessments_updated += 1
                else:
                    assessment = Assessment(
                        subject_id=subject_db_id,
                        assessment_date=_parsed_date,
                        cycle_number=cycle,
                        visit_name=visit_name or None,
                        baseline_sum=0.0,
                        current_sum=0.0,
                        change_percent=0.0,
                        batch_id=batch.id,
                        notes=f"EDC导入 - {timepoint_label}"
                    )
                    db.add(assessment)
                    db.flush()
                    assessments_created += 1

                # 同步 visit_name（已有评估的重复导入场景）
                if visit_name:
                    assessment.visit_name = visit_name

                # 写入靶病灶
                target_dicts = []
                for tl_raw in target_lesions_raw:
                    tl = TargetLesion(
                        assessment_id=assessment.id,
                        name=_safe_str(tl_raw.get("name") or tl_raw.get("病灶名称")),
                        location=_safe_str(tl_raw.get("location") or tl_raw.get("位置") or tl_raw.get("病灶所在器官")),
                        description=_safe_str(tl_raw.get("description") or tl_raw.get("病灶所在器官具体描述")),
                        lesion_id=_safe_str(tl_raw.get("lesion_id")),
                        baseline_size=_safe_float(
                            tl_raw.get("baseline_size") or tl_raw.get("基线最长径(mm)") or tl_raw.get("基线最长径")
                        ),
                        current_size=_safe_float(
                            tl_raw.get("current_size") or tl_raw.get("当前最长径(mm)") or tl_raw.get("当前最长径")
                        ),
                        size_unit=_safe_str(tl_raw.get("size_unit")) or "mm",
                        sum_diameter=_safe_float(tl_raw.get("sum_diameter")),
                        is_checked=bool(_safe_str(tl_raw.get("is_checked")).lower() in ("true", "1", "是", "yes")),
                        exam_date=_safe_str(tl_raw.get("exam_date")),
                        exam_method=_safe_str(tl_raw.get("exam_method")),
                        other_exam_method=_safe_str(tl_raw.get("other_exam_method")),
                        is_split_fused=_safe_str(tl_raw.get("is_split_fused")),
                        split_fuse_detail=_safe_str(tl_raw.get("split_fuse_detail")),
                        unmeasurable_reason=_safe_str(tl_raw.get("unmeasurable_reason")),
                        # 当前(随访)检查信息
                        current_is_checked=_safe_bool(tl_raw.get("current_is_checked")),
                        current_exam_date=_safe_str(tl_raw.get("current_exam_date")),
                        current_exam_method=_safe_str(tl_raw.get("current_exam_method")),
                        current_other_exam_method=_safe_str(tl_raw.get("current_other_exam_method")),
                        current_is_split_fused=_safe_str(tl_raw.get("current_is_split_fused")),
                        current_split_fuse_detail=_safe_str(tl_raw.get("current_split_fuse_detail")),
                    )
                    db.add(tl)
                    target_dicts.append({
                        "name": tl.name,
                        "location": tl.location,
                        "description": tl.description,
                        "lesion_id": tl.lesion_id,
                        "baseline_size": tl.baseline_size,
                        "current_size": tl.current_size,
                        "size_unit": tl.size_unit,
                        "sum_diameter": tl.sum_diameter,
                        "is_checked": tl.is_checked,
                        "exam_date": tl.exam_date,
                        "exam_method": tl.exam_method,
                        "other_exam_method": tl.other_exam_method,
                        "is_split_fused": tl.is_split_fused,
                        "split_fuse_detail": tl.split_fuse_detail,
                        "unmeasurable_reason": tl.unmeasurable_reason,
                        "current_is_checked": tl.current_is_checked,
                        "current_exam_date": tl.current_exam_date,
                        "current_exam_method": tl.current_exam_method,
                        "current_other_exam_method": tl.current_other_exam_method,
                        "current_is_split_fused": tl.current_is_split_fused,
                        "current_split_fuse_detail": tl.current_split_fuse_detail,
                    })

                # 写入非靶病灶
                non_target_dicts = []
                for ntl_raw in non_target_lesions_raw:
                    raw_status = _safe_str(ntl_raw.get("status") or ntl_raw.get("状态") or "持续存在")
                    if "进展" in raw_status or "恶化" in raw_status or raw_status.upper() == "PD":
                        status = "进展"
                    elif "消失" in raw_status or "完全缓解" in raw_status or raw_status.upper() == "CR":
                        status = "消失"
                    else:
                        status = "持续存在"

                    ntl = NonTargetLesion(
                        assessment_id=assessment.id,
                        name=_safe_str(ntl_raw.get("name") or ntl_raw.get("病灶名称")),
                        location=_safe_str(ntl_raw.get("location") or ntl_raw.get("位置") or ntl_raw.get("病灶所在器官")),
                        description=_safe_str(ntl_raw.get("description") or ntl_raw.get("病灶所在器官具体描述")),
                        lesion_id=_safe_str(ntl_raw.get("lesion_id")),
                        baseline_status=_safe_str(ntl_raw.get("baseline_status") or "持续存在"),
                        status=status,
                        baseline_is_checked=_safe_bool(ntl_raw.get("baseline_is_checked")),
                        current_is_checked=_safe_bool(ntl_raw.get("current_is_checked")),
                        exam_date=_safe_str(ntl_raw.get("exam_date")),
                        exam_method=_safe_str(ntl_raw.get("exam_method")),
                        current_exam_date=_safe_str(ntl_raw.get("current_exam_date")),
                        current_exam_method=_safe_str(ntl_raw.get("current_exam_method")),
                    )
                    db.add(ntl)
                    non_target_dicts.append({
                        "name": ntl.name,
                        "location": ntl.location,
                        "description": ntl.description,
                        "lesion_id": ntl.lesion_id,
                        "baseline_status": ntl.baseline_status,
                        "status": ntl.status,
                        "baseline_is_checked": ntl.baseline_is_checked,
                        "current_is_checked": ntl.current_is_checked,
                        "exam_date": ntl.exam_date,
                        "exam_method": ntl.exam_method,
                        "current_exam_date": ntl.current_exam_date,
                        "current_exam_method": ntl.current_exam_method,
                    })

                # 写入新病灶
                new_lesion_details = tp.get("new_lesion_details", [])
                for nl_raw in new_lesion_details:
                    nl = NewLesion(
                        assessment_id=assessment.id,
                        name=_safe_str(nl_raw.get("name") or nl_raw.get("病灶名称")),
                        location=_safe_str(nl_raw.get("location") or nl_raw.get("位置") or nl_raw.get("病灶所在器官")),
                        description=_safe_str(nl_raw.get("description") or nl_raw.get("病灶所在器官具体描述")),
                        lesion_id=_safe_str(nl_raw.get("lesion_id")),
                        exam_date=_safe_str(nl_raw.get("exam_date")),
                        exam_method=_safe_str(nl_raw.get("exam_method")),
                        other_exam_method=_safe_str(nl_raw.get("other_exam_method")),
                        notes=_safe_str(nl_raw.get("notes")),
                    )
                    db.add(nl)

                # 计算 baseline_sld（首次出现靶病灶时）
                current_sld = sum(t.get("current_size", 0) or 0 for t in target_dicts)
                baseline_sld_for_this = sum(t.get("baseline_size", 0) or 0 for t in target_dicts)
                if cycle == 1 and target_dicts:
                    baseline_sld = baseline_sld_for_this

                # 更新 nadir
                if nadir_sld is None:
                    nadir_sld = current_sld
                elif current_sld > 0:
                    nadir_sld = min(nadir_sld, current_sld)

                # 调用 RECIST 引擎
                result = RecistEngine.perform_assessment(
                    target_lesions=target_dicts,
                    non_target_lesions=non_target_dicts,
                    has_new_lesion=has_new_lesion,
                    tumor_marker_normal=tumor_marker_normal,
                    nadir_sum=nadir_sld,
                    target_not_applicable=(not has_tl and not target_dicts),
                    non_target_not_applicable=(not has_ntl and not non_target_dicts),
                )

                # ===== 保存引擎原始值（用于「程序」列）=====
                engine_overall = result.overall_status
                engine_target = result.target_status
                engine_non_target = result.non_target_status

                # ===== 人工(Excel)评估结论仅写入 manual_* 字段（见下方第 418-424 行）=====
                # 程序判定理由（target/non_target/overall_reason）保持 RECIST 引擎原始值，
                # 不混入任何"人工(Excel)评估"文本——「程序判定理由」列/tooltip 只展示引擎判定依据。

                # 程序列始终用引擎计算值（不受人工覆盖）
                assessment.target_status = engine_target
                assessment.non_target_status = engine_non_target
                assessment.overall_status = engine_overall
                # reason 为 RECIST 引擎的纯程序判定理由（不含人工文本）
                assessment.target_reason = result.target_reason
                assessment.non_target_reason = result.non_target_reason
                assessment.overall_reason = result.overall_reason
                assessment.baseline_sum = result.baseline_sum
                assessment.current_sum = result.current_sum
                assessment.change_percent = result.change_percent
                assessment.nadir_sum = result.nadir_sum
                assessment.change_from_nadir_pct = result.change_from_nadir_pct
                assessment.absolute_change = result.absolute_change
                assessment.has_new_lesion = has_new_lesion
                assessment.tumor_marker_normal = tumor_marker_normal

                # 保存人工评估结果（用于一致性比对）
                if human:
                    assessment.manual_target_status = human.get("tl_human") or None
                    assessment.manual_non_target_status = human.get("ntl_human") or None
                    assessment.manual_overall_status = human.get("overall_human") or None
                    nl_human = human.get("nl_human", "")
                    assessment.manual_has_new_lesion = (nl_human == "New Lesion")

                # 综合评估兜底：当缺少逐病灶尺寸明细、程序按 SLD 无法计算而被误判为 NE 时，
                # 使用 Excel 人工(靶/非靶/新病灶)分类按 RECIST 决策矩阵综合推导，
                # 避免「基线无病灶 → 一概 NE」的误判。
                if result.overall_status == "NE":
                    comp = RecistEngine.assess_comprehensive(
                        assessment.manual_target_status,
                        assessment.manual_non_target_status,
                        assessment.manual_has_new_lesion,
                    )
                    assessment.target_status = comp["target_status"]
                    assessment.non_target_status = comp["non_target_status"]
                    assessment.overall_status = comp["overall_status"]
                    assessment.overall_reason = comp["overall_reason"]

                risk_score = IntelligentAnalyzer.calculate_risk_score({
                    "change_percent": result.change_percent,
                    "has_new_lesion": has_new_lesion,
                    "non_target_status": result.non_target_status,
                    "tumor_marker_normal": tumor_marker_normal,
                })
                assessment.risk_score = risk_score
                assessment.raw_data = {
                    "target_lesions": target_dicts,
                    "non_target_lesions": non_target_dicts,
                    "new_lesion_details": tp.get("new_lesion_details", []),
                    "timepoint": timepoint_label,
                    "nadir_sum": nadir_sld,
                }

                total_assessments += 1

    else:
        # === 简化格式导入（向后兼容）===
        # 按 subject_id 分组病灶数据
        target_by_subject: Dict[str, list] = {}
        for row in parsed_data["target_lesions"]:
            cleaned = DataProcessor.clean_data(row)
            subj_id = cleaned.get("subject_id") or cleaned.get("受试者ID")
            if not subj_id or str(subj_id) not in subjects_map:
                continue
            target_by_subject.setdefault(str(subj_id), []).append(cleaned)

        non_target_by_subject: Dict[str, list] = {}
        for row in parsed_data["non_target_lesions"]:
            cleaned = DataProcessor.clean_data(row)
            subj_id = cleaned.get("subject_id") or cleaned.get("受试者ID")
            if not subj_id or str(subj_id) not in subjects_map:
                continue
            non_target_by_subject.setdefault(str(subj_id), []).append(cleaned)

        all_subject_ids = set(subjects_map.keys())
        all_subject_ids.update(target_by_subject.keys())
        all_subject_ids.update(non_target_by_subject.keys())

        for subj_id in all_subject_ids:
            subject_db_id = subjects_map.get(subj_id)
            if not subject_db_id:
                continue

            target_rows = target_by_subject.get(subj_id, [])
            non_target_rows = non_target_by_subject.get(subj_id, [])

            # 查找该受试者的最新评估
            assessment = db.query(Assessment).filter(
                Assessment.subject_id == subject_db_id
            ).order_by(Assessment.cycle_number.desc()).first()

            # 获取历史评估的 nadir
            history = db.query(Assessment).filter(
                Assessment.subject_id == subject_db_id
            ).order_by(Assessment.cycle_number).all()
            nadir_sld = None
            for h in history:
                if nadir_sld is None:
                    nadir_sld = h.current_sum or 0
                elif h.current_sum and h.current_sum > 0:
                    nadir_sld = min(nadir_sld, h.current_sum)

            # 新周期号 = 历史数量 + 1
            next_cycle = len(history) + 1

            # 简化格式：尝试从病灶行取检查日期作为评估日期
            _simple_date = None
            for _sr in (target_rows or []):
                _sd = _safe_str(_sr.get("exam_date") or _sr.get("current_exam_date") or "")
                if _sd:
                    try:
                        _simple_date = datetime.fromisoformat(_sd)
                    except (ValueError, TypeError):
                        pass
                    break
            if _simple_date is None:
                for _sr in (non_target_rows or []):
                    _sd = _safe_str(_sr.get("exam_date") or _sr.get("current_exam_date") or "")
                    if _sd:
                        try:
                            _simple_date = datetime.fromisoformat(_sd)
                        except (ValueError, TypeError):
                            pass
                        break
            if _simple_date is None:
                _simple_date = datetime.now(timezone.utc)

            # 创建新的评估（始终追加，不覆盖）
            assessment = Assessment(
                subject_id=subject_db_id,
                assessment_date=_simple_date,
                cycle_number=next_cycle,
                baseline_sum=0.0,
                current_sum=0.0,
                change_percent=0.0,
                batch_id=batch.id,
                notes="imported"
            )
            db.add(assessment)
            db.flush()
            assessments_created += 1

            # 写入靶病灶
            target_dicts = []
            for row in target_rows:
                tl = TargetLesion(
                    assessment_id=assessment.id,
                    name=str(row.get("name") or row.get("病灶名称") or ""),
                    location=str(row.get("location") or row.get("位置") or ""),
                    baseline_size=_safe_float(row.get("baseline_size") or row.get("基线最长径(mm)") or row.get("基线最长径")),
                    current_size=_safe_float(row.get("current_size") or row.get("当前最长径(mm)") or row.get("当前最长径")),
                    exam_date=_safe_str(row.get("exam_date")),
                    exam_method=_safe_str(row.get("exam_method")),
                )
                db.add(tl)
                target_dicts.append({
                    "name": tl.name,
                    "location": tl.location,
                    "baseline_size": tl.baseline_size,
                    "current_size": tl.current_size,
                    "exam_date": tl.exam_date,
                    "exam_method": tl.exam_method,
                })

            # 写入非靶病灶
            non_target_dicts = []
            for row in non_target_rows:
                raw_status = str(row.get("status") or row.get("状态") or "持续存在").strip()
                if "进展" in raw_status or "恶化" in raw_status or raw_status.upper() == "PD":
                    status = "进展"
                elif "消失" in raw_status or "完全缓解" in raw_status or raw_status.upper() == "CR":
                    status = "消失"
                else:
                    status = "持续存在"

                ntl = NonTargetLesion(
                    assessment_id=assessment.id,
                    name=str(row.get("name") or row.get("病灶名称") or ""),
                    location=str(row.get("location") or row.get("位置") or ""),
                    baseline_status=_safe_str(row.get("baseline_status") or "持续存在"),
                    status=status,
                    exam_date=_safe_str(row.get("exam_date")),
                    exam_method=_safe_str(row.get("exam_method")),
                )
                db.add(ntl)
                non_target_dicts.append({
                    "name": ntl.name,
                    "location": ntl.location,
                    "baseline_status": ntl.baseline_status,
                    "status": ntl.status,
                    "exam_date": ntl.exam_date,
                    "exam_method": ntl.exam_method,
                })

            # 从 Excel 读取 has_new_lesion 和 tumor_marker_normal
            has_new_lesion = False
            tumor_marker_normal = True
            if target_rows:
                first = target_rows[0]
                has_new_flag = first.get("new_lesion") or first.get("新病灶") or first.get("has_new_lesion")
                if has_new_flag and str(has_new_flag).strip().lower() in ("是", "yes", "true", "1"):
                    has_new_lesion = True
            if non_target_rows:
                first = non_target_rows[0]
                tmn_flag = first.get("tumor_marker") or first.get("肿瘤标志物") or first.get("tumor_marker_normal")
                if tmn_flag and str(tmn_flag).strip().lower() in ("否", "no", "false", "0", "异常"):
                    tumor_marker_normal = False

            # 调用 RECIST 引擎
            result = RecistEngine.perform_assessment(
                target_lesions=target_dicts,
                non_target_lesions=non_target_dicts,
                has_new_lesion=has_new_lesion,
                tumor_marker_normal=tumor_marker_normal,
                nadir_sum=nadir_sld,
            )

            assessment.target_status = result.target_status
            assessment.target_reason = result.target_reason
            assessment.non_target_status = result.non_target_status
            assessment.non_target_reason = result.non_target_reason
            assessment.overall_status = result.overall_status
            assessment.overall_reason = result.overall_reason
            assessment.baseline_sum = result.baseline_sum
            assessment.current_sum = result.current_sum
            assessment.change_percent = result.change_percent
            assessment.absolute_change = result.absolute_change
            assessment.has_new_lesion = has_new_lesion
            assessment.tumor_marker_normal = tumor_marker_normal

            risk_score = IntelligentAnalyzer.calculate_risk_score({
                "change_percent": result.change_percent,
                "has_new_lesion": has_new_lesion,
                "non_target_status": result.non_target_status,
                "tumor_marker_normal": tumor_marker_normal,
            })
            assessment.risk_score = risk_score
            assessment.raw_data = {
                "target_lesions": target_dicts,
                "non_target_lesions": non_target_dicts,
            }

            total_assessments += 1

    batch.total_assessments = total_assessments
    batch.subjects_count = len(subjects_map)
    db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库写入失败: {str(e)}")
    except Exception as e:
        db.rollback()
        detail = f"导入处理异常: {type(e).__name__}: {str(e)}"
        # 开发/调试环境附加完整 traceback（生产环境可去掉 tb.format_exc()）
        import os
        if os.environ.get("DEBUG", "").lower() in ("1", "true"):
            detail += f"\n{tb.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)

    return {
        "message": "导入成功",
        "format": fmt,
        "batch_id": batch.id,
        "subjects_created": subjects_created,
        "subjects_updated": len(subjects_map) - subjects_created,
        "assessments_created": assessments_created,
        "assessments_updated": assessments_updated,
        "total_assessments": total_assessments,
    }


@router.get("/export")
async def export_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出所有数据为Excel（仅当前用户的数据）"""
    user_subject_ids = db.query(Subject.id).filter(
        Subject.user_id == current_user.id
    ).subquery()

    subjects = db.query(Subject).filter(Subject.user_id == current_user.id).all()
    assessments = db.query(Assessment).filter(
        Assessment.subject_id.in_(user_subject_ids)
    ).all()

    subjects_data = [
        {
            "受试者ID": s.subject_id,
            "姓名": s.name,
            "性别": s.gender,
            "年龄": s.age,
            "诊断": s.diagnosis,
            "基线日期": s.baseline_date.isoformat() if s.baseline_date else "",
            "创建时间": s.created_at.isoformat() if s.created_at else ""
        }
        for s in subjects
    ]

    assessments_data = [
        {
            "受试者ID": a.subject_id,
            "评估日期": a.assessment_date.isoformat() if a.assessment_date else "",
            "周期": a.cycle_number,
            "靶病灶状态": a.target_status,
            "非靶病灶状态": a.non_target_status,
            "整体状态": a.overall_status,
            "基线总和": a.baseline_sum,
            "当前总和": a.current_sum,
            "变化率": a.change_percent,
            "风险评分": a.risk_score,
            "新病灶": "是" if a.has_new_lesion else "否"
        }
        for a in assessments
    ]

    excel_data = DataProcessor.export_to_excel(subjects_data, assessments_data)

    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=recist_data_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )
