"""AI 助手问答接口（检索式，不依赖外部大模型）

意图识别：
  1) 标准信息  —— 检索 RECIST 1.1 算法说明
  2) 受试者信息 —— 按编号查询受试者 + 评估，返回摘要与可点击链接
  3) 评估结果  —— 返回当前批次统计（分布 / ORR / DCR / 一致性）
  4) 兜底帮助  —— 说明能力并给出示例问题

所有数据均来自本系统现有接口，患者数据不出内网，无 token 成本。
"""
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.database import User, Subject, Assessment
from app.services.recist_engine import RecistEngine
from app.api.analysis import get_statistics

router = APIRouter(prefix="/api/chat", tags=["AI助手"])


class ChatRequest(BaseModel):
    message: str
    batch_id: Optional[int] = None


class ChatLink(BaseModel):
    label: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    links: List[ChatLink] = []
    suggestions: List[str] = []


# ───────────────────────── 工具函数 ─────────────────────────

def _extract_subject_code(message: str) -> Optional[str]:
    """从用户消息中提取受试者编号（如 S01005）。"""
    m = re.search(r'[Ss][\d]{3,}', message)
    if m:
        return m.group(0).upper()
    m2 = re.search(r'受试者[^0-9A-Za-z]*([A-Za-z]?[\d]{3,})', message)
    if m2:
        raw = m2.group(1).upper()
        return raw if raw[0].isalpha() else 'S' + raw
    return None


def _build_link_url(subject_id: int, batch_id: Optional[int]) -> str:
    return f"/subjects/{subject_id}" + (f"?batch={batch_id}" if batch_id else "")


def _latest_assessment(assessments: List[Assessment]):
    if not assessments:
        return None
    return sorted(
        assessments,
        key=lambda a: ((a.assessment_date or datetime.min), a.id or 0)
    )[-1]


# ───────────────────────── 意图处理 ─────────────────────────

def _handle_standard() -> ChatResponse:
    algo = RecistEngine.get_algorithm_summary()
    desc = algo.get("description", "实体瘤疗效评价标准第 1.1 版")
    t_rules = algo.get("target_lesion_rules", [])
    n_rules = algo.get("non_target_lesion_rules", [])
    crit = algo.get("critical_details", [])

    lines = [f"📘 {desc}", "", "【靶病灶判定】"]
    for r in t_rules:
        lines.append(f"· {r['status']}：{r['condition'].replace(chr(10), '；')}")
    lines.append("")
    lines.append("【非靶病灶判定】")
    for r in n_rules:
        lines.append(f"· {r['status']}：{r['condition'].replace(chr(10), '；')}")
    lines.append("")
    lines.append("【关键提醒】")
    for c in crit[:3]:
        lines.append(f"· {c}")
    lines.append("")
    lines.append("完整阈值、决策矩阵与流程图见「评估标准」页。")

    return ChatResponse(
        reply="\n".join(lines),
        links=[ChatLink(label="查看完整评估标准", url="/standard")],
        suggestions=[
            "RECIST 1.1 里 PD 是怎么判定的？",
            "CR 和 PR 需要确认吗？",
            "什么情况下会出现新病灶判 PD？",
        ],
    )


def _handle_subject_list(db: Session, user: User, batch_id: Optional[int]) -> ChatResponse:
    query = db.query(Subject).filter(Subject.user_id == user.id)
    if batch_id is not None:
        from sqlalchemy import distinct
        batch_subj_ids = db.query(Assessment.subject_id).filter(
            Assessment.batch_id == batch_id
        ).distinct().subquery()
        query = query.filter(or_(Subject.batch_id == batch_id, Subject.id.in_(batch_subj_ids)))
    subjects = query.order_by(Subject.subject_id).all()

    if not subjects:
        return ChatResponse(
            reply="当前账号下暂无可查询的受试者。请先在「数据导入」页导入 EDC 数据，或在「受试者」页手动新增。",
            links=[ChatLink(label="前往数据导入", url="/upload")],
            suggestions=["如何导入 EDC 数据？", "评估标准是什么？"],
        )

    lines = [f"当前共有 {len(subjects)} 名受试者（按编号排序，列出前 10 名，点击查看详情）：", ""]
    links = []
    for s in subjects[:10]:
        subj_assess = s.assessments
        if batch_id is not None:
            subj_assess = [a for a in subj_assess if a.batch_id == batch_id]
        latest = _latest_assessment(subj_assess)
        latest_text = (
            f"最新疗效：{latest.manual_overall_status or latest.overall_status or 'NE'}"
            if latest else "暂无评估"
        )
        lines.append(f"· {s.subject_id}（{s.name or '未命名'}）— {latest_text}")
        links.append(ChatLink(label=f"查看 {s.subject_id}", url=_build_link_url(s.id, batch_id)))

    if len(subjects) > 10:
        lines.append("")
        lines.append(f"…还有 {len(subjects) - 10} 名，更多可在「受试者」页查看。")

    return ChatResponse(
        reply="\n".join(lines),
        links=links,
        suggestions=["受试者 S01005 的基本情况", "当前批次的疗效统计"],
    )


def _handle_subject_detail(db: Session, user: User, code: str, batch_id: Optional[int]) -> ChatResponse:
    candidates = {code}
    if not code[0].isalpha():
        candidates.add("S" + code)
    subject = db.query(Subject).filter(
        Subject.user_id == user.id,
        Subject.subject_id.in_(candidates)
    ).first()
    if not subject:
        return ChatResponse(
            reply=f"未找到编号为「{code}」的受试者。请确认编号是否正确（如 S01005），或在「受试者」页查看全部。",
            links=[ChatLink(label="前往受试者列表", url="/subjects")],
            suggestions=["列出所有受试者", "当前批次的疗效统计"],
        )

    subj_assess = subject.assessments
    if batch_id is not None:
        subj_assess = [a for a in subj_assess if a.batch_id == batch_id]
    latest = _latest_assessment(subj_assess)

    info = [
        f"【受试者 {subject.subject_id}】（{subject.name or '未命名'}）",
        f"性别：{subject.gender or '—'}　年龄：{subject.age if subject.age is not None else '—'}　诊断：{subject.diagnosis or '—'}",
        f"本批次评估周期数：{len(subj_assess)}",
    ]
    if latest:
        eff = latest.manual_overall_status or latest.overall_status or "NE"
        man = latest.manual_overall_status or "（无人工录入）"
        info.append("")
        info.append(f"最新周期（周期{latest.cycle_number or '?'} / {latest.assessment_date.strftime('%Y-%m-%d') if latest.assessment_date else '—'}）：")
        info.append(f"  总体疗效：系统={latest.overall_status or 'NE'}　人工={man}　→ 采用 {eff}")
        info.append(f"  靶病灶：{latest.target_status or '—'}；非靶病灶：{latest.non_target_status or '—'}；新病灶：{'有' if latest.has_new_lesion else '无'}")
        if latest.baseline_sum is not None and latest.current_sum is not None:
            info.append(f"  SLD：基线 {round(latest.baseline_sum, 1)}mm → 当前 {round(latest.current_sum, 1)}mm（变化 {round(latest.change_percent or 0, 1)}%）")
    else:
        info.append("本批次暂无评估记录，可点击下方链接查看受试者基础信息。")
    info.append("")
    info.append("点击链接查看完整详情（含所有周期病灶明细与趋势图）。")

    return ChatResponse(
        reply="\n".join(info),
        links=[ChatLink(label=f"查看 {subject.subject_id} 完整详情", url=_build_link_url(subject.id, batch_id))],
        suggestions=[
            "当前批次的疗效统计",
            "哪些受试者评估与人工不一致？",
            "RECIST 1.1 的 PD 怎么判定？",
        ],
    )


async def _handle_statistics(db: Session, user: User, batch_id: Optional[int]) -> ChatResponse:
    stats = await get_statistics(batch_id, db, user)
    total_subjects = stats.get("total_subjects", 0)
    total_assess = stats.get("total_assessments", 0)
    dist = stats.get("status_distribution", {}) or {}
    orr = stats.get("response_rate", 0)
    dcr = stats.get("disease_control_rate", 0)
    match = stats.get("match_count", 0)
    mismatch = stats.get("mismatch_count", 0)
    match_rate = stats.get("match_rate", 0)

    def _cnt(key):
        return dist.get(key, 0)

    lines = [
        "【当前批次疗效统计】",
        f"受试者：{total_subjects} 名　评估记录：{total_assess} 条",
        f"疗效分布：CR {_cnt('CR')} · PR {_cnt('PR')} · SD {_cnt('SD')} · PD {_cnt('PD')} · NE {_cnt('NE')}",
        f"客观缓解率 ORR（CR+PR）：{orr}%　疾病控制率 DCR（CR+PR+SD）：{dcr}%",
        f"系统 vs 人工 一致：{match}　不一致：{mismatch}（一致率 {match_rate}%）",
    ]
    if mismatch and mismatch > 0:
        lines.append("")
        lines.append(f"存在 {mismatch} 条不一致，可在「智能分析」页查看不一致清单并一键下发质疑。")

    links = [ChatLink(label="查看智能分析", url="/analysis")]
    if batch_id is not None:
        links.append(ChatLink(label="查看受试者列表", url="/subjects"))
    return ChatResponse(
        reply="\n".join(lines),
        links=links,
        suggestions=[
            "哪些受试者评估与人工不一致？",
            "列出所有受试者",
            "RECIST 1.1 的 PD 怎么判定？",
        ],
    )


def _handle_help() -> ChatResponse:
    return ChatResponse(
        reply=(
            "👋 我是 RECIST 评估助手，可以基于本系统的真实数据回答您的问题：\n\n"
            "1) 标准信息：RECIST 1.1 的判定规则、阈值、PD/CR 确认等；\n"
            "2) 受试者信息：输入「受试者 S01005」查某位受试者的基本情况与疗效，并给出可点击的详情链接；\n"
            "3) 评估结果：当前批次的疗效分布、ORR/DCR、系统 vs 人工一致性等统计。\n\n"
            "试试下面的问题："
        ),
        links=[],
        suggestions=[
            "受试者 S01005 的基本情况",
            "当前批次的疗效统计",
            "哪些受试者评估与人工不一致？",
            "RECIST 1.1 里 PD 是怎么判定的？",
        ],
    )


# ───────────────────────── 路由 ─────────────────────────

STANDARD_KW = ["recist", "标准", "算法", "判定", "怎么评估", "是什么意思", "定义", "阈值", "决策矩阵", "cr", "pr", "sd", "pd", "确认"]
RESULT_KW = ["统计", "结果", "疗效", "评估", "多少", "不一致", "分布", "总体", "orr", "dcr", "客观缓解", "疾病控制"]
SUBJECT_KW = ["受试者", "编号", "列表", "哪些受试者", "受试者信息", "基本情况"]


@router.post("/", response_model=ChatResponse)
async def chat_route(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保留 router 形式（供 include_router 使用）；主应用改为在 main.py 内联注册。"""
    return await handle_chat(req, db, current_user)


async def handle_chat(
    req: ChatRequest,
    db: Session,
    current_user: User,
):
    msg = (req.message or "").strip()
    if not msg:
        return _handle_help()

    low = msg.lower()
    code = _extract_subject_code(msg)

    # 1) 命中受试者编号 → 优先返回该受试者详情
    if code:
        return _handle_subject_detail(db, current_user, code, req.batch_id)

    # 2) 询问受试者列表
    if any(k in msg for k in SUBJECT_KW):
        return _handle_subject_list(db, current_user, req.batch_id)

    # 3) 标准信息
    if any(k in low for k in STANDARD_KW):
        return _handle_standard()

    # 4) 评估结果统计
    if any(k in low for k in RESULT_KW):
        return await _handle_statistics(db, current_user, req.batch_id)

    # 5) 兜底
    return _handle_help()
