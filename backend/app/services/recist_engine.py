"""RECIST 1.1 评估引擎 — 与标准判定规则完全对齐（6.1 靶病灶 / 6.2 非靶病灶 / 6.3 确认规则）

═══════════════════════════════════════════════════════════════
RECIST 1.1 疗效评估算法
═══════════════════════════════════════════════════════════════

【核心概念】
  SLD (Sum of Longest Diameters) = Σ 各靶病灶最长径（基线）
  SLD_nadir = min(SLD_baseline, SLD_followup_1, SLD_followup_2, ...)
    → 治疗期间出现的最低值（含基线），PD 判定参照 nadir 而非基线

【6.1 靶病灶判定】
  ┌─────────────┬──────────────────────────────────────────────┐
  │ CR 完全缓解  │ 所有靶病灶消失；所有病理淋巴结短轴 < 10 mm   │
  │ PR 部分缓解  │ 靶病灶 SLD 较基线下降 ≥30%                   │
  │ SD 疾病稳定  │ 既达不到 PR（缩小不足），也未达 PD（增大不足），│
  │             │ 介于两者之间                                  │
  │ PD 疾病进展  │ 满足以下任一：                                │
  │             │ ① SLD 较研究期间最小值(nadir,含基线)           │
  │             │   增加≥20% 且绝对值增加≥5 mm；                 │
  │             │ ② 出现新病灶                                   │
  └─────────────┴──────────────────────────────────────────────┘

  公式：
    PR: (SLD_baseline - SLD_now) / SLD_baseline ≥ 0.30
    PD: (SLD_now - SLD_nadir) / SLD_nadir ≥ 0.20 AND (SLD_now - SLD_nadir) ≥ 5 mm
        或 出现新病灶

  ⚠️ 三个极易出错的细节：
    1. PD 参照是 nadir（最低值），不是基线。
       例：基线100→最低50→复查60：相对+20%(=+60) 且绝对+10mm≥5 → 判PD。
       若回升到58(+16%<20%) 则仍SD。
    2. PD 双条件缺一不可：既需相对+20%，又需绝对+5mm。
       小病灶微小波动不应误判为进展。
    3. 新病灶 = PD，无论大小、无论出现在何处（含 FDG-PET 发现）。

【6.2 非靶病灶判定】
  ┌──────────────────┬────────────────────────────────────────┐
  │ CR               │ 所有非靶病灶消失；所有淋巴结短轴 < 10 mm │
  │ 非CR/非PD(IR/SD) │ 存在≥1个非靶病灶，或肿瘤标志物持续高于正常│
  │ PD               │ 已有非靶病灶明确进展，或出现任何新病灶    │
  └──────────────────┴────────────────────────────────────────┘

  ⚠️ 非靶PD的"明确"二字：非靶病灶的轻微增大不构成PD，
     必须是明确(unequivocal)进展（如胸水从少量到大量、淋巴管炎从局限到弥漫）。
     系统实现时切忌把非靶尺寸小幅变化自动判为PD。

【6.3 确认规则 (Confirmation)】
  · 在非随机试验中，CR与PR须在治疗后≥4周复查确认。
  · 随机试验可由方案决定是否需确认（多数不强制），
    但确认性的PR后续访视中视为"持续PR"，直至满足PD标准——
    后续判定参照nadir而非基线。
  · PD一般不需确认（除非影像模棱两可）。

【整体评价决策流程（图1）】
  计算SLD → 所有靶病灶消失? → CR
         → 否 → 继续判定 → SLD较基线↓≥30%? → PR
         → 是/否 → 较nadir↑≥20%且绝对↑≥5mm或新病灶? → PD
         → 否 → SD(介于PR与PD之间)
  → 再与非靶病灶结果合并 → 总体疗效

【整体评价决策矩阵】
  ┌──────────┬──────────────────┬──────────────┬──────────┐
  │ Target   │ Non-Target       │ New Lesion   │ Overall  │
  ├──────────┼──────────────────┼──────────────┼──────────┤
  │ CR       │ CR               │ No           │ CR       │
  │ CR       │ Non-CR/Non-PD    │ No           │ PR       │
  │ PR       │ Non-PD/Non-CR    │ No           │ PR       │
  │ SD       │ Non-PD/Non-CR    │ No           │ SD       │
  │ PD       │ Any              │ No/Yes       │ PD       │
  │ Any      │ PD               │ No/Yes       │ PD       │
  │ Any      │ Any              │ Yes          │ PD       │ ←最高优先级
  └──────────┴──────────────────┴──────────────┴──────────┘
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


def _fmt_tl(lesions: List[Dict[str, Any]]) -> str:
    """把靶病灶列表格式化为可读明细（器官(描述): 基线→当前mm）"""
    items = []
    for l in lesions:
        nm = l.get("name") or l.get("location") or "病灶"
        b = l.get("baseline_size") or 0
        c = l.get("current_size") or 0
        items.append(f"{nm}({b:.0f}→{c:.0f}mm)")
    return "；".join(items)


def _fmt_ntl(lesions: List[Dict[str, Any]]) -> str:
    """把非靶病灶列表格式化为可读明细（器官(描述): 状态）"""
    items = []
    for l in lesions:
        nm = l.get("name") or l.get("location") or "病灶"
        st = l.get("status") or "持续存在"
        items.append(f"{nm}:{st}")
    return "；".join(items)


class RecistStatus(str, Enum):
    """RECIST评估状态"""
    CR = "CR"                      # 完全缓解
    PR = "PR"                      # 部分缓解
    SD = "SD"                      # 疾病稳定（仅用于靶病灶）
    PD = "PD"                      # 疾病进展
    NE = "NE"                      # 无法评估
    NON_CR_NON_PD = "Non-CR/Non-PD"  # 非完全缓解/非疾病进展（非靶病灶标准表述）


class NonTargetStatus(str, Enum):
    """非靶病灶状态"""
    DISAPPEARED = "消失"
    PERSISTENT = "持续存在"
    PROGRESSED = "进展"


@dataclass
class AssessmentResult:
    """评估结果数据类"""
    target_status: str
    target_reason: str
    non_target_status: str
    non_target_reason: str
    overall_status: str
    overall_reason: str
    baseline_sum: float
    current_sum: float
    nadir_sum: float = 0.0
    change_percent: float = 0.0
    change_from_nadir_pct: Optional[float] = None
    absolute_change: float = 0.0
    target_not_applicable: bool = False
    non_target_not_applicable: bool = False


class RecistEngine:
    """RECIST 1.1 评估引擎"""

    # 评估阈值（与 6.1 靶病灶判定标准完全对齐）
    PR_THRESHOLD = -30.0               # 部分缓解：SLD较基线下降≥30%
    PD_PERCENT_THRESHOLD = 20.0        # 进展：SLD较nadir增加≥20%
    PD_ABSOLUTE_THRESHOLD = 5.0        # 进展：绝对值增加≥5mm
    LYMPH_NODE_SHORT_AXIS_MAX = 10.0   # CR 判定：病理/淋巴结短轴须 < 10mm

    RESPONSE_CN = {
        "CR": "完全缓解（CR）",
        "PR": "部分缓解（PR）",
        "SD": "疾病稳定（SD）",
        "PD": "疾病进展（PD）",
        "NE": "不可评估（NE）",
        "Non-CR/Non-PD": "非完全缓解/非疾病进展（Non-CR/Non-PD）",
        "No New Lesion": "无新病灶",
        "New Lesion → PD": "有新病灶 → PD",
    }

    @staticmethod
    def calculate_sum(lesions: List[Dict[str, Any]], field: str) -> float:
        """计算病灶最长径总和"""
        return sum(lesion.get(field, 0) or 0 for lesion in lesions)

    @classmethod
    def assess_target_lesions(
        cls,
        target_lesions: List[Dict[str, Any]],
        has_new_lesion: bool = False,
        nadir_sum: Optional[float] = None,
        target_not_applicable: bool = False
    ) -> Tuple[str, str, float, float, float, Optional[float], bool]:
        """
        评估靶病灶（RECIST 1.1 标准）

        PD 判定改为与最低点(nadir)比较而非基线，支持多周期评估。

        Returns:
            (status, reason, baseline_sum, current_sum, change_percent, change_from_nadir_pct, not_applicable)
        """
        # 受试者无靶病灶 → NE（不影响整体评估）
        if target_not_applicable:
            return RecistStatus.NE, "受试者无靶病灶，不参与靶病灶评估", 0.0, 0.0, 0.0, None, True

        baseline_sum = cls.calculate_sum(target_lesions, "baseline_size")
        current_sum = cls.calculate_sum(target_lesions, "current_size")

        if not target_lesions:
            return RecistStatus.NE, "无靶病灶数据", 0.0, 0.0, 0.0, None, False

        if baseline_sum == 0:
            return RecistStatus.NE, "基线数据缺失", baseline_sum, current_sum, 0.0, None, False

        change_percent = ((current_sum - baseline_sum) / baseline_sum) * 100
        detail = _fmt_tl(target_lesions)

        # nadir: 历史最低 SLD，默认等于基线
        effective_nadir = nadir_sum if nadir_sum is not None else baseline_sum
        if effective_nadir > 0:
            change_from_nadir_pct = ((current_sum - effective_nadir) / effective_nadir) * 100
            nadir_absolute_change = abs(current_sum - effective_nadir)
        else:
            change_from_nadir_pct = None
            nadir_absolute_change = 0.0

        # 新病灶标记（靶病灶层面记录，整体评估时统一判断）
        if has_new_lesion:
            return (
                RecistStatus.PD,
                f"[{detail}] 检出新病灶。依据 RECIST 1.1 新病灶规则（任何新病灶出现即一票否决为 PD）："
                f"整体疗效判为疾病进展(PD)。",
                baseline_sum, current_sum, change_percent,
                change_from_nadir_pct, False
            )

        # 所有靶病灶消失 → CR
        # 标准：所有靶病灶消失；所有病理淋巴结短轴 < 10 mm
        if current_sum == 0:
            return (
                RecistStatus.CR,
                f"[{detail}] 所有靶病灶最长(非淋巴结)/最短(淋巴结)直径之和(SLD)=0mm。"
                f"依据 RECIST 1.1 靶病灶完全缓解(CR)标准：所有靶病灶消失"
                f"（且病理淋巴结短轴<{cls.LYMPH_NODE_SHORT_AXIS_MAX:.0f}mm），判为 CR。",
                baseline_sum, current_sum, change_percent,
                change_from_nadir_pct, False
            )

        # 疾病进展（较nadir增加≥20% 且绝对值增加≥5mm）
        # 标准：PD参照是nadir(最低值)，不是基线；双条件缺一不可
        if (change_from_nadir_pct is not None
                and change_from_nadir_pct >= cls.PD_PERCENT_THRESHOLD
                and nadir_absolute_change >= cls.PD_ABSOLUTE_THRESHOLD):
            return (
                RecistStatus.PD,
                f"[{detail}] 基线SLD={baseline_sum:.1f}mm，当前SLD={current_sum:.1f}mm，"
                f"Nadir(研究期间最小值,含基线)={effective_nadir:.1f}mm；"
                f"SLD较nadir增加{change_from_nadir_pct:.1f}%（≥+20%）且绝对值增加{nadir_absolute_change:.1f}mm（≥+5mm）。"
                f"依据 RECIST 1.1 靶病灶疾病进展(PD)标准（双条件：相对↑≥20% 且 绝对↑≥5mm），判为 PD。",
                baseline_sum, current_sum, change_percent,
                change_from_nadir_pct, False
            )

        # 部分缓解（SLD较基线下降≥30%）
        if change_percent <= cls.PR_THRESHOLD:
            return (
                RecistStatus.PR,
                f"[{detail}] 基线SLD={baseline_sum:.1f}mm，当前SLD={current_sum:.1f}mm，"
                f"较基线减少{abs(change_percent):.1f}%（≥30%）。"
                f"依据 RECIST 1.1 靶病灶部分缓解(PR)标准（SLD较基线↓≥30%），判为 PR。",
                baseline_sum, current_sum, change_percent,
                change_from_nadir_pct, False
            )

        # 疾病稳定（既达不到PR缩小不足，也未达PD增大不足，介于两者之间）
        return (
            RecistStatus.SD,
            f"[{detail}] 基线SLD={baseline_sum:.1f}mm，当前SLD={current_sum:.1f}mm，"
            f"较基线变化{change_percent:+.1f}%；"
            f"既未达PR（↓≥30%），也未达PD（较nadir↑≥20%且绝对↑≥5mm）。"
            f"依据 RECIST 1.1 靶病灶疾病稳定(SD)标准（介于PR与PD之间），判为 SD。",
            baseline_sum, current_sum, change_percent,
            change_from_nadir_pct, False
        )

    @classmethod
    def assess_non_target_lesions(
        cls,
        non_target_lesions: List[Dict[str, Any]],
        tumor_marker_normal: bool = True,
        non_target_not_applicable: bool = False
    ) -> Tuple[str, str, bool]:
        """
        评估非靶病灶（RECIST 1.1 标准 — 6.2 非靶病灶判定）

        标准：
          CR: 所有非靶病灶消失；所有淋巴结短轴 < 10 mm
          非CR/非PD (IR/SD): 存在≥1个非靶病灶，或肿瘤标志物持续高于正常
          PD: 已有非靶病灶明确进展(unequivocal)，或出现任何新病灶

        ⚠️ 非靶PD的"明确"二字：轻微增大不构成PD，
           必须是明确进展（胸水少量→大量、淋巴管炎局限→弥漫等）。
           系统切忌把尺寸小幅变化自动判为PD。

        Returns:
            (status, reason, not_applicable)
        """
        # 受试者无非靶病灶 → NE（不影响整体评估）
        if non_target_not_applicable:
            return RecistStatus.NE, "受试者无非靶病灶，不参与非靶病灶评估", True

        if not non_target_lesions:
            return RecistStatus.NE, "无非靶病灶数据", False

        statuses = [lesion.get("status", "") for lesion in non_target_lesions]
        detail = _fmt_ntl(non_target_lesions)

        # 任何明确(unequivocal)进展 → PD
        if NonTargetStatus.PROGRESSED.value in statuses:
            return RecistStatus.PD, (
                f"[{detail}] 至少一个非靶病灶明确(unequivocal)进展。"
                f"依据 RECIST 1.1 非靶病灶PD标准(6.2)：明确进展 → PD。"
                f"注：非靶PD须为'明确'进展，轻微增大不构成PD。"
            ), False

        # 是否全部消失
        all_disappeared = all(s == NonTargetStatus.DISAPPEARED.value for s in statuses)
        any_persistent = any(s == NonTargetStatus.PERSISTENT.value for s in statuses)

        # CR: 所有非靶病灶消失 + 淋巴结短轴 < 10mm（+ 肿瘤标志物正常）
        if all_disappeared and tumor_marker_normal:
            return RecistStatus.CR, (
                f"[{detail}] 所有非靶病灶消失"
                f"（且淋巴结短轴<{cls.LYMPH_NODE_SHORT_AXIS_MAX:.0f}mm，肿瘤标志物正常）。"
                f"依据 RECIST 1.1 非靶病灶完全缓解(CR)标准(6.2)，判为非靶病灶 CR。"
            ), False

        if all_disappeared and not tumor_marker_normal:
            return RecistStatus.NON_CR_NON_PD, (
                f"[{detail}] 非靶病灶消失但肿瘤标志物未恢复正常。"
                f"依据 RECIST 1.1 非靶病灶标准(6.2)，判为 Non-CR/Non-PD(IR/SD)。"
            ), False

        if any_persistent:
            return RecistStatus.NON_CR_NON_PD, (
                f"[{detail}] 存在≥1个非靶病灶持续存在，无明确(unequivocal)进展。"
                f"依据 RECIST 1.1 非靶病灶标准(6.2)：持续存在但非明确进展 → Non-CR/Non-PD(IR/SD)。"
                f"注：非靶病灶轻微增大不构成PD，必须是明确进展。"
            ), False

        # 混合/其他情况：保守判为 Non-CR/Non-PD (IR/SD)
        return RecistStatus.NON_CR_NON_PD, (
            f"[{detail}] 非靶病灶未完全消失且无明确进展，存在非靶病灶或标志物异常。"
            f"依据 RECIST 1.1 非靶病灶标准(6.2)，判为 Non-CR/Non-PD(IR/SD)。"
        ), False

    @classmethod
    def assess_overall(
        cls,
        target_status: str,
        non_target_status: str,
        has_new_lesion: bool,
        target_not_applicable: bool = False,
        non_target_not_applicable: bool = False
    ) -> Tuple[str, str]:
        """
        整体疗效评价（RECIST 1.1 决策矩阵）

        标准结果只有五种: CR, PR, SD, PD, NE
        Non-CR/Non-PD 仅在无可评估靶病灶且非靶病灶持续存在时作为描述性结果。

        not_applicable 表示受试者基线无此类病灶（如无靶病灶），该维度不参与整体评估。
        与 NE（无法评估，存在但数据不足）区分。

        Returns:
            (status, reason)
        """
        tl = target_status
        ntl = non_target_status

        def _v(s):
            """兼容 enum 与 str 输入：返回底层状态值用于文案展示。"""
            return s.value if isinstance(s, RecistStatus) else s

        # === Rule 1: 任何新病灶 → PD（最高优先级）===
        if has_new_lesion:
            return RecistStatus.PD, (
                f"依据 RECIST 1.1 整体疗效评价决策矩阵（新病灶一票否决，最高优先级）："
                f"检出新病灶（靶病灶: {_v(tl)}，非靶病灶: {_v(ntl)}），整体疗效直接判为疾病进展(PD)。"
            )

        # === Rule 2: 靶病灶 PD → PD ===
        if tl == RecistStatus.PD and not target_not_applicable:
            return RecistStatus.PD, (
                f"依据 RECIST 1.1 整体决策矩阵（靶病灶 PD → 整体 PD）："
                f"靶病灶判为 PD（非靶病灶: {_v(ntl)}，无新病灶），整体疗效 → PD。"
            )

        # === Rule 3: 非靶病灶明确进展 → PD ===
        if ntl == RecistStatus.PD and not non_target_not_applicable:
            return RecistStatus.PD, (
                f"依据 RECIST 1.1 整体决策矩阵（非靶病灶明确进展 → 整体 PD）："
                f"非靶病灶明确进展（靶病灶: {_v(tl)}，无新病灶），整体疗效 → PD。"
            )

        # === 处理 not_applicable 情况 ===

        # 双方都 not_applicable（既无靶病灶也无非靶病灶）
        if target_not_applicable and non_target_not_applicable:
            return RecistStatus.NE, "受试者基线既无靶病灶也无非靶病灶，无可评估病灶 → NE。"

        # 无靶病灶：整体跟随非靶病灶
        if target_not_applicable:
            if ntl == RecistStatus.CR:
                return RecistStatus.CR, "受试者无靶病灶，非靶病灶全部消失 → CR。"
            elif ntl == RecistStatus.NON_CR_NON_PD:
                return RecistStatus.NON_CR_NON_PD, "受试者无靶病灶，非靶病灶持续存在但无进展 → Non-CR/Non-PD。"
            elif ntl == RecistStatus.PD:
                return RecistStatus.PD, "受试者无靶病灶，非靶病灶明确进展 → PD。"
            else:
                return RecistStatus.NE, "受试者无靶病灶，非靶病灶亦不可评估 → NE。"

        # 无非靶病灶：整体跟随靶病灶
        if non_target_not_applicable:
            reason_map = {
                "CR": "受试者无非靶病灶，靶病灶全部消失 → CR。",
                "PR": "受试者无非靶病灶，靶病灶充分缩小 → PR。",
                "SD": "受试者无非靶病灶，靶病灶变化未达PR或PD → SD。",
                "PD": "受试者无非靶病灶，靶病灶进展 → PD。",
            }
            if tl in reason_map:
                return tl, reason_map[tl]
            return RecistStatus.NE, "受试者无非靶病灶，靶病灶亦不可评估 → NE。"

        # === 标准决策矩阵（双方都参与评估）===

        # 双方都不可评估
        if tl == RecistStatus.NE and ntl == RecistStatus.NE:
            return RecistStatus.NE, "靶病灶和非靶病灶均不可评估 → NE。"

        # 靶病灶不可评估 + 非靶病灶可评估
        if tl == RecistStatus.NE:
            if ntl == RecistStatus.CR:
                return RecistStatus.NE, "非靶病灶CR但靶病灶不可评估，无法确认是否为完全缓解 → NE。"
            elif ntl == RecistStatus.NON_CR_NON_PD:
                return RecistStatus.NON_CR_NON_PD, "靶病灶不可评估但非靶病灶持续存在 → Non-CR/Non-PD。"
            else:
                return RecistStatus.NE, "靶病灶不可评估，无法确定整体疗效 → NE。"

        # 非靶病灶不可评估 + 靶病灶可评估
        if ntl == RecistStatus.NE:
            if tl == RecistStatus.CR:
                return RecistStatus.PR, "靶病灶CR但非靶病灶不可评估，不能判为CR → PR。"
            elif tl == RecistStatus.PR:
                return RecistStatus.PR, "靶病灶PR（非靶病灶不可评估），靶病灶PR仍成立 → PR。"
            elif tl == RecistStatus.SD:
                return RecistStatus.SD, "靶病灶SD（非靶病灶不可评估），保守判断为SD。"
            else:
                return RecistStatus.NE, "非靶病灶不可评估，无法确定整体疗效 → NE。"

        # CR + CR → CR
        if tl == RecistStatus.CR and ntl == RecistStatus.CR:
            return RecistStatus.CR, "依据 RECIST 1.1 整体决策矩阵（CR+CR→CR）：靶病灶CR + 非靶病灶CR + 无新病灶 → 所有病灶消失 → 整体 CR。"

        # CR + Non-CR/Non-PD → PR
        if tl == RecistStatus.CR and ntl == RecistStatus.NON_CR_NON_PD:
            return RecistStatus.PR, "依据 RECIST 1.1 整体决策矩阵（CR+Non-CR/Non-PD→PR）：靶病灶CR但非靶病灶持续存在（Non-CR/Non-PD），不能判为CR → 整体 PR。"

        # PR + (CR 或 Non-CR/Non-PD) → PR
        if tl == RecistStatus.PR and ntl in (RecistStatus.CR, RecistStatus.NON_CR_NON_PD):
            return RecistStatus.PR, f"依据 RECIST 1.1 整体决策矩阵（PR+(CR/Non-CR/Non-PD)→PR）：靶病灶PR（非靶病灶: {_v(ntl)}），靶病灶负荷充分缩小 → 整体 PR。"

        # SD + (CR 或 Non-CR/Non-PD) → SD
        if tl == RecistStatus.SD and ntl in (RecistStatus.CR, RecistStatus.NON_CR_NON_PD):
            return RecistStatus.SD, f"依据 RECIST 1.1 整体决策矩阵（SD+(CR/Non-CR/Non-PD)→SD）：靶病灶SD（非靶病灶: {_v(ntl)}），未达到PR或PD标准 → 整体 SD。"

        # 兜底
        return RecistStatus.NE, f"无法确定整体评价：靶病灶={tl}，非靶病灶={ntl}。"

    @classmethod
    def assess_comprehensive(
        cls,
        target_human: Optional[str],
        non_target_human: Optional[str],
        has_new_lesion_human: Optional[bool]
    ) -> Dict[str, Any]:
        """
        综合评估（缺少逐病灶测量数据时）。

        当导入数据只含 Excel 的「人工(靶/非靶/新病灶)分类」、没有靶/非靶病灶尺寸明细，
        程序无法按 SLD 计算时，使用这三个人工分类按 RECIST 1.1 决策矩阵综合推导
        靶/非靶/总体疗效，避免「基线无病灶 → 一概 NE」的误判。

        映射规则：
          - 靶/非靶维度为「不适用(NA)」→ 该维度受试者基线无此类病灶(not_applicable)
          - CR/PR/SD/PD → 该维度对应状态
          - NE 或未知值 → 该维度不可评估(NE)
          - 新病灶(布尔) → 参与总体决策矩阵(任何新病灶 → PD)

        Returns:
            dict: {target_status, non_target_status, overall_status, overall_reason}
        """
        def norm(v):
            return (v or "").strip()

        t = norm(target_human)
        n = norm(non_target_human)
        has_new = bool(has_new_lesion_human)

        NA_VALUES = ("", "NA", "N/A", "不适用", "不适用（NA）", "不适用(NA)", "不适用（N/A）")

        # ---- 靶病灶维度 ----
        tl_na = t in NA_VALUES
        if tl_na:
            tl_status = None
        elif t in ("CR", "PR", "SD", "PD"):
            tl_status = t
        else:  # NE 或无法识别 → 不可评估
            tl_status = RecistStatus.NE

        # ---- 非靶病灶维度 ----
        ntl_na = n in NA_VALUES
        if ntl_na:
            ntl_status = None
        elif n == "CR":
            ntl_status = RecistStatus.CR
        elif n == "PD":
            ntl_status = RecistStatus.PD
        elif "NON-CR" in n.upper() or "非完全缓解" in n or "非疾病进展" in n:
            ntl_status = RecistStatus.NON_CR_NON_PD
        else:  # NE 或无法识别 → 不可评估
            ntl_status = RecistStatus.NE

        overall, reason = cls.assess_overall(
            tl_status if tl_status is not None else RecistStatus.NE,
            ntl_status if ntl_status is not None else RecistStatus.NE,
            has_new, tl_na, ntl_na
        )

        # 转为与 manual_* 字段一致的存储值（不适用 → 不适用（NA））
        stored_tl = "不适用（NA）" if tl_na else (tl_status or RecistStatus.NE)
        stored_ntl = "不适用（NA）" if ntl_na else (ntl_status or RecistStatus.NE)
        return {
            "target_status": stored_tl,
            "non_target_status": stored_ntl,
            "overall_status": overall,
            "overall_reason": reason,
        }

    @classmethod
    def perform_assessment(
        cls,
        target_lesions: List[Dict[str, Any]],
        non_target_lesions: List[Dict[str, Any]],
        has_new_lesion: bool = False,
        tumor_marker_normal: bool = True,
        nadir_sum: Optional[float] = None,
        target_not_applicable: bool = False,
        non_target_not_applicable: bool = False
    ) -> AssessmentResult:
        """
        执行完整 RECIST 1.1 评估

        Args:
            target_lesions: 靶病灶列表 [{"baseline_size": float, "current_size": float, ...}, ...]
            non_target_lesions: 非靶病灶列表 [{"status": "消失"/"持续存在"/"进展", ...}, ...]
            has_new_lesion: 是否有新病灶
            tumor_marker_normal: 肿瘤标志物是否正常
            nadir_sum: 历史最低 SLD（用于多周期 PD 判定）
            target_not_applicable: 受试者基线无靶病灶
            non_target_not_applicable: 受试者基线无非靶病灶
        """
        target_status, target_reason, baseline_sum, current_sum, change_percent, change_from_nadir_pct, tl_na = \
            cls.assess_target_lesions(target_lesions, has_new_lesion, nadir_sum, target_not_applicable)

        non_target_status, non_target_reason, ntl_na = \
            cls.assess_non_target_lesions(non_target_lesions, tumor_marker_normal, non_target_not_applicable)

        overall_status, overall_reason = cls.assess_overall(
            target_status, non_target_status, has_new_lesion,
            target_not_applicable or tl_na,
            non_target_not_applicable or ntl_na
        )

        return AssessmentResult(
            target_status=target_status,
            target_reason=target_reason,
            non_target_status=non_target_status,
            non_target_reason=non_target_reason,
            overall_status=overall_status,
            overall_reason=overall_reason,
            baseline_sum=baseline_sum,
            current_sum=current_sum,
            nadir_sum=nadir_sum if nadir_sum is not None else baseline_sum,
            change_percent=change_percent or 0.0,
            change_from_nadir_pct=change_from_nadir_pct,
            absolute_change=abs(current_sum - baseline_sum),
            target_not_applicable=target_not_applicable or tl_na,
            non_target_not_applicable=non_target_not_applicable or ntl_na
        )

    @classmethod
    def get_algorithm_summary(cls) -> Dict[str, Any]:
        """
        返回 RECIST 1.1 算法的完整结构化说明（与 6.1/6.2/6.3 标准完全对齐）。

        用于前端展示、API 文档（GET /api/assessments/algorithm）、报告页 Tooltip。
        """
        return {
            "algorithm": "RECIST 1.1",
            "version": "1.1",
            "description": "实体瘤疗效评价标准（Response Evaluation Criteria in Solid Tumors）第1.1版",
            # ── 阈值常量 ──
            "thresholds": {
                "pr_threshold": cls.PR_THRESHOLD,              # -30% (SLD较基线下降)
                "pd_percent_threshold": cls.PD_PERCENT_THRESHOLD,  # +20% (SLD较nadir增加)
                "pd_absolute_threshold": cls.PD_ABSOLUTE_THRESHOLD,  # +5mm (绝对增加)
                "lymph_node_short_axis_max": cls.LYMPH_NODE_SHORT_AXIS_MAX,  # 10mm (CR判定)
            },
            # ── 6.1 靶病灶判定 ──
            "target_lesion_rules": [
                {
                    "status": "CR 完全缓解",
                    "condition": "所有靶病灶消失；所有病理淋巴结短轴 < 10 mm"
                },
                {
                    "status": "PR 部分缓解",
                    "condition": f"靶病灶 SLD 较基线下降 ≥{abs(cls.PR_THRESHOLD):.0f}%"
                },
                {
                    "status": "SD 疾病稳定",
                    "condition": "既达不到 PR（缩小不足），也未达 PD（增大不足），介于两者之间"
                },
                {
                    "status": "PD 疾病进展",
                    "condition": (
                        f"满足以下任一：\n"
                        f"  ① SLD 较研究期间最小值(nadir,含基线)"
                        f" 增加 ≥+{cls.PD_PERCENT_THRESHOLD:.0f}% "
                        f"且 绝对值增加 ≥+{cls.PD_ABSOLUTE_THRESHOLD:.0f} mm；\n"
                        f"  ② 出现新病灶"
                    )
                },
            ],
            # ── 6.2 非靶病灶判定 ──
            "non_target_lesion_rules": [
                {
                    "status": "CR",
                    "condition": f"所有非靶病灶消失；所有淋巴结短轴 < {cls.LYMPH_NODE_SHORT_AXIS_MAX:.0f} mm"
                },
                {
                    "status": "非CR/非PD (IR/SD)",
                    "condition": "存在 ≥1 个非靶病灶，或肿瘤标志物持续高于正常"
                },
                {
                    "status": "PD",
                    "condition": "已有非靶病灶明确(unequivocal)进展，或出现任何新病灶。\n"
                               "⚠️ 轻微增大不构成PD，必须是明确进展。"
                },
            ],
            # ── 6.3 确认规则 ──
            "confirmation_rules": [
                "在非随机试验中，CR 与 PR 须在治疗后 ≥4 周复查确认。",
                "随机试验可由方案决定是否需确认（多数不强制）。",
                "确认性的 PR 后续访视中视为「持续 PR」，直至满足 PD 标准——后续判定参照 nadir 而非基线。",
                "PD 一般不需确认（除非影像模棱两可）。"
            ],
            # ── 三个极易出错的细节 ──
            "critical_details": [
                "PD 参照是 nadir（最低值），不是基线。"
                "例：基线100→最低50→复查60：相对最低值+20%(=+60) 且绝对+10mm≥5 → 判PD。"
                "若回升到58(+16%<20%) 则仍SD。",
                "PD 双条件缺一不可：既需相对+20%，又需绝对+5mm。小病灶微小波动不应误判为进展。",
                "新病灶 = PD，无论大小、无论出现在何处（含 FDG-PET 发现）。"
            ],
            # ── 公式 ──
            "formulas": {
                "SLD_baseline": "Σ 各靶病灶最长径（基线）",
                "SLD_nadir": "min(SLD_baseline, SLD_followup_1, SLD_followup_2, ...)",
                "PR": "(SLD_baseline - SLD_now) / SLD_baseline ≥ 0.30",
                "PD": (
                    "(SLD_now - SLD_nadir) / SLD_nadir ≥ 0.20 "
                    "AND (SLD_now - SLD_nadir) ≥ 5 mm  → 或  出现新病灶"
                ),
            },
            # ── 整体优先级规则 ──
            "overall_priority_rules": [
                {"priority": 1, "rule": "新病灶出现 → PD（最高优先级，覆盖其他一切）"},
                {"priority": 2, "rule": "非靶病灶明确(unequivocal)进展 → PD"},
                {"priority": 3, "rule": "靶病灶 PD（较nadir↑≥20% 且 绝对↑≥5mm）→ PD"},
                {"priority": 4, "rule": "标准矩阵匹配 → CR/PR/SD/PD/NE"},
            ],
            # ── 决策矩阵 ──
            "decision_matrix": [
                ["Target", "Non-Target", "New Lesion", "Overall"],
                ["CR", "CR", "No", "CR"],
                ["CR", "Non-CR/Non-PD", "No", "PR"],
                ["PR", "Non-CR/Non-PD or CR", "No", "PR"],
                ["SD", "Non-CR/Non-PD or CR", "No", "SD"],
                ["PD", "Any", "Any", "PD"],
                ["Any", "PD", "Any", "PD"],
                ["Any", "Any", "Yes", "PD"],
            ],
            # ── 关键概念 ──
            "key_concepts": {
                "SLD": "Sum of Longest Diameters — 所有靶病灶最长直径之和",
                "Baseline SLD": "筛选期(基线)各靶病灶最长径之和，后续比较的基准",
                "Nadir SLD": "研究期间出现的最低 SLD 值（含基线），PD 判定与之比较而非基线",
                "Target Lesions": "可测量病灶（通常每个器官最多选2个，最多5个总计）",
                "Non-Target Lesions": "不可测量病灶（如胸腔积液、骨转移、淋巴管播散等）",
                "New Lesion": "治疗过程中新出现的任何病灶，出现即判为 PD（无论大小、位置、发现方式）",
                "Unequivocal Progression": "非靶病灶的'明确'进展（如胸水从少量到大量、淋巴管炎从局限到弥漫）；轻微增大不构成PD",
            },
            # ── 判定流程图（图1 文字描述）──
            "flowchart_steps": [
                {"step": 1, "action": "计算 SLD（最长径之和）"},
                {"step": 2, "action": "所有靶病灶消失？", "yes": "CR（节点<10mm）", "no": "继续"},
                {"step": 3, "action": "SLD 较基线 ↓≥30%？", "yes": "PR", "no": "继续"},
                {"step": 4, "action": "较 nadir ↑≥20% 且 绝对↑≥5mm，或新病灶？", "yes": "PD", "no": "SD（介于PR与PD之间）"},
                {"step": 5, "action": "再与非靶病灶结果合并 → 总体疗效"},
            ],
        }
