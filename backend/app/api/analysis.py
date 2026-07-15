"""智能分析API"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List, Dict, Any
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.database import User, Assessment, Subject, ImportBatch
from app.schemas.schemas import TrendAnalysis, StatisticsResponse
from app.services.intelligent_analyzer import IntelligentAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["智能分析"])


def _user_subject_ids(db: Session, user: User):
    """返回当前用户拥有的受试者ID子查询"""
    return db.query(Subject.id).filter(Subject.user_id == user.id).subquery()


@router.post("/batches/clear")
async def clear_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """一键清空当前用户的全部导入批次（级联删除全部评估、病灶及受试者）"""
    batches = db.query(ImportBatch).filter(
        ImportBatch.user_id == current_user.id
    ).all()
    if not batches:
        return {"deleted": 0}

    user_subs = _user_subject_ids(db, current_user)
    assessments = db.query(Assessment).filter(
        Assessment.subject_id.in_(user_subs)
    ).all()
    for a in assessments:
        db.delete(a)
    db.flush()
    subjects = db.query(Subject).filter(Subject.user_id == current_user.id).all()
    for s in subjects:
        db.delete(s)
    for b in batches:
        db.delete(b)
    db.commit()
    return {"deleted": len(batches)}


@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除单条导入批次（级联删除该批次下全部评估及病灶，并清理已无评估的受试者）"""
    batch = db.query(ImportBatch).filter(
        ImportBatch.id == batch_id,
        ImportBatch.user_id == current_user.id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    user_subs = _user_subject_ids(db, current_user)
    assessments = db.query(Assessment).filter(
        Assessment.batch_id == batch_id,
        Assessment.subject_id.in_(user_subs)
    ).all()

    affected_subject_ids = {a.subject_id for a in assessments}
    for a in assessments:
        db.delete(a)  # 级联删除靶/非靶病灶
    db.delete(batch)
    db.flush()  # 先落库，便于统计受试者剩余评估数

    # 清理已无任何评估记录的受试者
    for sid in affected_subject_ids:
        remaining = db.query(Assessment).filter(Assessment.subject_id == sid).count()
        if remaining == 0:
            subj = db.query(Subject).filter(Subject.id == sid).first()
            if subj:
                db.delete(subj)

    db.commit()
    return {"deleted": True, "batch_id": batch_id}


def _generate_recist_analysis(assessments, trend, prediction):
    """基于 RECIST 1.1 标准生成详细的趋势分析"""
    analysis = []

    if not assessments:
        return analysis

    latest = assessments[-1]
    sorted_assessments = sorted(assessments, key=lambda x: x.cycle_number or 0)

    # 1. 靶病灶 SLD 趋势分析
    sld_values = [a.current_sum for a in sorted_assessments if a.current_sum and a.current_sum > 0]
    if len(sld_values) >= 2:
        baseline_sld = sorted_assessments[0].current_sum or 0
        latest_sld = sld_values[-1]
        nadir_sld = min(sld_values)

        if baseline_sld > 0:
            change_from_baseline = (latest_sld - baseline_sld) / baseline_sld * 100
            if change_from_baseline <= -30:
                analysis.append({
                    "icon": "✓",
                    "text": f"靶病灶最长径之和(SLD)较基线缩小 {abs(change_from_baseline):.1f}%，已达到 PR 标准（≥30%缩小），提示治疗有效"
                })
            elif change_from_baseline >= 20:
                analysis.append({
                    "icon": "⚠",
                    "text": f"靶病灶SLD较基线增大 {change_from_baseline:.1f}%，已达到 PD 标准（≥20%增大），提示疾病进展"
                })
            else:
                analysis.append({
                    "icon": "→",
                    "text": f"靶病灶SLD较基线变化 {change_from_baseline:.1f}%，处于疾病稳定(SD)范围（-30%~+20%）"
                })

        # nadir 分析
        if nadir_sld > 0 and latest_sld > nadir_sld:
            change_from_nadir = (latest_sld - nadir_sld) / nadir_sld * 100
            if change_from_nadir >= 20:
                analysis.append({
                    "icon": "🔴",
                    "text": f"当前SLD较最低点(nadir)增大 {change_from_nadir:.1f}%，已超过 PD 阈值（+20%），符合 RECIST 1.1 疾病进展标准"
                })
            elif change_from_nadir >= 10:
                analysis.append({
                    "icon": "🟡",
                    "text": f"当前SLD较最低点(nadir)增大 {change_from_nadir:.1f}%，接近 PD 阈值（+20%），需密切关注"
                })
            else:
                analysis.append({
                    "icon": "🟢",
                    "text": f"当前SLD较最低点(nadir)增大 {change_from_nadir:.1f}%，尚未接近 PD 阈值"
                })

    # 2. 预测下一周期
    if prediction.get("predicted_status") and prediction.get("predicted_status") != "NE":
        pred_status = prediction["predicted_status"]
        pred_change = prediction.get("predicted_change_percent")
        confidence = prediction.get("confidence", 0)

        pred_text = {
            "CR": "完全缓解(CR) - 肿瘤完全消失",
            "PR": "部分缓解(PR) - 肿瘤缩小≥30%",
            "SD": "疾病稳定(SD) - 肿瘤变化在-30%~+20%之间",
            "PD": "疾病进展(PD) - 肿瘤增大≥20%或出现新病灶",
            "Non-CR/Non-PD": "非完全缓解/非疾病进展(Non-CR/Non-PD)"
        }.get(pred_status, pred_status)

        change_str = f"，预测变化率 {pred_change:.1f}%" if pred_change is not None else ""
        analysis.append({
            "icon": "📊",
            "text": f"基于历史数据线性回归预测，下一周期评估结果可能为：{pred_text}{change_str}（置信度 {confidence*100:.0f}%）"
        })

    # 3. 趋势方向分析
    trend_dir = trend.get("trend_direction", "stable")
    avg_change = trend.get("avg_change_percent", 0)
    improving = trend.get("improving_cycles", 0)
    worsening = trend.get("worsening_cycles", 0)

    if trend_dir == "improving":
        analysis.append({
            "icon": "📉",
            "text": f"整体呈改善趋势（改善周期{improving}次，恶化周期{worsening}次），平均变化率 {avg_change}%，治疗反应良好，预计未来病情继续好转"
        })
    elif trend_dir == "worsening":
        analysis.append({
            "icon": "📈",
            "text": f"整体呈恶化趋势（改善周期{improving}次，恶化周期{worsening}次），平均变化率 {avg_change}%，需警惕疾病进展，建议考虑调整治疗方案"
        })
    else:
        analysis.append({
            "icon": "📊",
            "text": f"整体病情稳定（改善周期{improving}次，恶化周期{worsening}次），平均变化率 {avg_change}%，预计未来维持当前状态"
        })

    # 4. 新病灶分析
    new_lesion_cycles = [a for a in sorted_assessments if a.has_new_lesion]
    if new_lesion_cycles:
        latest_nl = new_lesion_cycles[-1]
        analysis.append({
            "icon": "⚠",
            "text": f"已出现新病灶（最近一次在周期{latest_nl.cycle_number}），根据 RECIST 1.1 标准，新病灶出现即判定为疾病进展(PD)，需密切关注后续评估"
        })
    else:
        analysis.append({
            "icon": "✓",
            "text": "截至目前未出现新病灶，无新发病灶进展征象"
        })

    # 5. 非靶病灶分析
    ntl_statuses = [a.non_target_status for a in sorted_assessments if a.non_target_status]
    if ntl_statuses:
        latest_ntl = ntl_statuses[-1]
        if latest_ntl == "PD":
            analysis.append({
                "icon": "🔴",
                "text": "非靶病灶出现明确进展，根据 RECIST 1.1 标准，非靶病灶进展(PD)即判定整体疗效为疾病进展"
            })
        elif latest_ntl == "CR":
            analysis.append({
                "icon": "✓",
                "text": "非靶病灶已完全消失，提示治疗效果良好"
            })
        else:
            analysis.append({
                "icon": "→",
                "text": "非靶病灶维持稳定状态，未见明确进展或消失"
            })

    # 6. 综合预测
    latest_status = latest.overall_status
    if latest_status == "PD":
        analysis.append({
            "icon": "🔴",
            "text": "综合以上分析，当前已处于疾病进展状态。依据 RECIST 1.1 标准，建议及时调整治疗方案，考虑换药或联合治疗策略"
        })
    elif latest_status == "PR" and trend_dir == "improving":
        analysis.append({
            "icon": "🟢",
            "text": "综合以上分析，当前治疗有效且呈持续改善趋势。预计未来可能进一步缩小，有望达到完全缓解(CR)。建议继续当前治疗方案并密切随访"
        })
    elif latest_status == "SD" and trend_dir == "worsening":
        analysis.append({
            "icon": "🟡",
            "text": "综合以上分析，当前病情虽稳定但有恶化趋势。若下一周期SLD继续增大并超过nadir的20%，将触发PD判定。建议提前评估是否需要调整治疗方案"
        })
    elif latest_status == "SD":
        analysis.append({
            "icon": "→",
            "text": "综合以上分析，当前病情稳定。预计未来大概率维持SD状态，按计划进行下一周期评估即可"
        })
    elif latest_status == "CR":
        analysis.append({
            "icon": "✓",
            "text": "综合以上分析，已达完全缓解。重点监测复发风险，定期复查影像学确认"
        })

    return analysis


@router.get("/batches", response_model=List[Dict[str, Any]])
async def list_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的导入批次列表"""
    batches = db.query(ImportBatch).filter(
        ImportBatch.user_id == current_user.id
    ).order_by(ImportBatch.import_time.desc()).all()
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "import_time": b.import_time.isoformat() if b.import_time else None,
            "total_assessments": b.total_assessments,
            "subjects_count": b.subjects_count,
        }
        for b in batches
    ]


@router.get("/trend/{subject_id}", response_model=Dict[str, Any])
async def analyze_subject_trend(
    subject_id: int,
    batch_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分析单个受试者的趋势（可选按批次隔离，避免不同导入批次的评估被重复计入）"""
    subject_obj = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id
    ).first()
    if not subject_obj:
        raise HTTPException(status_code=404, detail="受试者不存在")

    query = db.query(Assessment).filter(Assessment.subject_id == subject_id)
    if batch_id:
        query = query.filter(Assessment.batch_id == batch_id)
    assessments = query.order_by(Assessment.cycle_number).all()

    if not assessments:
        raise HTTPException(status_code=404, detail="该受试者无评估记录")

    history = [
        {
            "cycle_number": a.cycle_number,
            "visit_name": a.visit_name,
            "change_percent": a.change_percent,
            "overall_status": a.overall_status,
            "target_status": a.target_status,
            "non_target_status": a.non_target_status,
            "has_new_lesion": a.has_new_lesion,
            "current_sld": a.current_sum,
            "baseline_sld": a.baseline_sum,
            "nadir_sld": a.nadir_sum,
            "change_from_nadir_pct": a.change_from_nadir_pct,
            "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None
        }
        for a in assessments
    ]

    trend = IntelligentAnalyzer.analyze_trend(history)
    prediction = IntelligentAnalyzer.predict_next_status(history)
    anomalies = IntelligentAnalyzer.detect_anomalies(history)

    # 基于 RECIST 1.1 标准生成详细趋势分析
    recist_analysis = _generate_recist_analysis(assessments, trend, prediction)

    recommendations = IntelligentAnalyzer.generate_recommendations(
        current_status=assessments[-1].overall_status,
        risk_score=assessments[-1].risk_score or 0,
        trend=trend
    )

    return {
        "subject_id": subject_obj.subject_id,
        "subject_name": subject_obj.name or "",
        "subject_db_id": subject_id,
        "trend": trend,
        "prediction": prediction,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "recist_analysis": recist_analysis,
        "historical_data": history
    }


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics(
    batch_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取总体统计数据及详细评估表格（按用户隔离，可选按批次筛选）"""
    # 获取当前用户的受试者ID集合
    user_subject_ids = db.query(Subject.id).filter(
        Subject.user_id == current_user.id
    ).subquery()

    query = db.query(Assessment).options(
        selectinload(Assessment.subject),
        selectinload(Assessment.target_lesions),
        selectinload(Assessment.non_target_lesions)
    ).filter(Assessment.subject_id.in_(user_subject_ids))

    if batch_id:
        query = query.filter(Assessment.batch_id == batch_id)

    all_assessments = query.all()

    # 受试者维度：当前批次下「无评估记录」的受试者也要在概览中体现（所有表同步）
    assessment_subject_ids = {a.subject_id for a in all_assessments}
    if batch_id:
        candidate_subjects = db.query(Subject).filter(
            Subject.user_id == current_user.id,
            or_(Subject.batch_id == batch_id, Subject.id.in_(assessment_subject_ids))
        ).all()
    else:
        candidate_subjects = db.query(Subject).filter(
            Subject.user_id == current_user.id
        ).all()
    subject_only = [s for s in candidate_subjects if s.id not in assessment_subject_ids]

    # 获取用户批次列表
    batches = db.query(ImportBatch).filter(
        ImportBatch.user_id == current_user.id
    ).order_by(ImportBatch.import_time.desc()).all()
    batch_list = [
        {
            "id": b.id,
            "filename": b.filename,
            "import_time": b.import_time.isoformat() if b.import_time else None,
            "total_assessments": b.total_assessments,
            "subjects_count": b.subjects_count,
        }
        for b in batches
    ]

    if not all_assessments and not subject_only:
        return {
            "total_subjects": 0,
            "total_assessments": 0,
            "status_distribution": {},
            "status_counts": {},
            "response_rate": 0.0,
            "disease_control_rate": 0.0,
            "average_change_percent": 0.0,
            "recent_assessments": [],
            "assessment_table": [],
            "batches": batch_list
        }

    # 计算各状态分布（按总体疗效）
    # 有效状态：优先使用 Excel 人工评估(总体疗效评估)，缺省时回退程序自动判定
    def _eff_overall(a):
        return a.manual_overall_status or a.overall_status or "NE"

    def _eff_target(a):
        return a.manual_target_status or a.target_status or "NE"

    def _eff_ntl(a):
        return a.manual_non_target_status or a.non_target_status or "NE"

    status_dist = {}
    for a in all_assessments:
        status = _eff_overall(a)
        status_dist[status] = status_dist.get(status, 0) + 1

    # 靶病灶评估分布（详细分类）
    target_dist = {}
    for a in all_assessments:
        status = _eff_target(a)
        target_dist[status] = target_dist.get(status, 0) + 1

    # 非靶病灶评估分布（详细分类）
    ntl_dist = {}
    for a in all_assessments:
        status = _eff_ntl(a)
        ntl_dist[status] = ntl_dist.get(status, 0) + 1

    # 新病灶分布（程序 or 人工任一判定为有即计为"有"）
    new_lesion_count = sum(
        1 for a in all_assessments if (a.manual_has_new_lesion or a.has_new_lesion)
    )

    # 自动↔人工一致性统计（仅针对有总体疗效评估的记录）
    match_count = 0
    mismatch_count = 0
    no_human_count = 0
    for a in all_assessments:
        if not a.manual_overall_status:
            no_human_count += 1
        elif a.manual_overall_status == a.overall_status:
            match_count += 1
        else:
            mismatch_count += 1

    comparable = match_count + mismatch_count
    match_rate = round(match_count / comparable * 100, 1) if comparable > 0 else 0.0
    latest_by_subject = {}
    for a in all_assessments:
        sid = a.subject_id
        if sid not in latest_by_subject or (a.cycle_number or 0) > (latest_by_subject[sid].cycle_number or 0):
            latest_by_subject[sid] = a

    latest_data = [
        {
            "subject_id": a.subject_id,
            "cycle_number": a.cycle_number,
            "visit_name": a.visit_name,
            "overall_status": _eff_overall(a),
            "change_percent": a.change_percent
        }
        for a in latest_by_subject.values()
    ]

    orr = IntelligentAnalyzer.calculate_response_rate(latest_data)
    dcr = IntelligentAnalyzer.calculate_disease_control_rate(latest_data)

    # 平均变化率
    avg_change = sum(a.change_percent or 0 for a in all_assessments) / len(all_assessments) if all_assessments else 0.0

    # 最近评估：按受试者聚合，取每个受试者最新一条，最多3个
    recent_by_subject = {}
    for a in sorted(all_assessments, key=lambda x: x.created_at or datetime.min, reverse=True):
        sid = a.subject_id
        if sid not in recent_by_subject:
            recent_by_subject[sid] = a
        if len(recent_by_subject) >= 3:
            break

    recent_data = []
    for a in recent_by_subject.values():
        recent_data.append({
            "id": a.id,
            "subject_id": a.subject.subject_id if a.subject else str(a.subject_id),
            "subject_db_id": a.subject_id,
            "subject_name": a.subject.name if a.subject else "",
            "cycle_number": a.cycle_number,
            "visit_name": a.visit_name,
            "overall_status": a.overall_status,
            "change_percent": a.change_percent,
            "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None
        })

    # 详细评估表格：所有评估记录，含靶病灶/非靶病灶/新病灶/总体疗效/判断理由
    assessment_table = []
    for a in sorted(all_assessments, key=lambda x: (x.subject_id, x.cycle_number or 0)):
        target_lesions = [
            {"name": l.name, "location": l.location, "baseline_size": l.baseline_size, "current_size": l.current_size}
            for l in a.target_lesions
        ]
        non_target_lesions = [
            {"name": l.name, "location": l.location, "status": l.status}
            for l in a.non_target_lesions
        ]

        assessment_table.append({
            "id": a.id,
            "subject_id": a.subject.subject_id if a.subject else str(a.subject_id),
            "subject_db_id": a.subject_id,
            "subject_name": a.subject.name if a.subject else "",
            "cycle_number": a.cycle_number,
            "visit_name": a.visit_name,
            "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None,
            "timepoint": (a.raw_data or {}).get("timepoint", ""),
            "target_status": a.target_status or "NE",
            "target_reason": a.target_reason or "",
            "non_target_status": a.non_target_status or "NE",
            "non_target_reason": a.non_target_reason or "",
            "has_new_lesion": a.has_new_lesion or False,
            "new_lesion_text": "有新病灶" if a.has_new_lesion else "无新病灶",
            "overall_status": a.overall_status or "NE",
            "overall_reason": a.overall_reason or "",
            "effective_status": _eff_overall(a),
            "effective_target_status": _eff_target(a),
            "effective_non_target_status": _eff_ntl(a),
            "manual_target_status": a.manual_target_status or "",
            "manual_non_target_status": a.manual_non_target_status or "",
            "manual_overall_status": a.manual_overall_status or "",
            "manual_has_new_lesion": a.manual_has_new_lesion or False,
            "target_match": (a.manual_target_status and a.manual_target_status == a.target_status),
            "non_target_match": (a.manual_non_target_status and a.manual_non_target_status == a.non_target_status),
            "overall_match": (a.manual_overall_status and a.manual_overall_status == a.overall_status),
            "has_manual_data": bool(a.manual_overall_status),
            "baseline_sum": a.baseline_sum,
            "current_sum": a.current_sum,
            "nadir_sum": a.nadir_sum,
            "change_percent": a.change_percent,
            "change_from_nadir_pct": a.change_from_nadir_pct,
            "target_lesions": target_lesions,
            "non_target_lesions": non_target_lesions,
        })

    # 独立受试者数（含无评估记录的受试者）
    unique_subjects = len(set(a.subject_id for a in all_assessments) | {s.id for s in subject_only})

    # 追加「无评估记录」的受试者行，使首页概览与其余页面同步显示
    for s in sorted(subject_only, key=lambda x: x.subject_id):
        assessment_table.append({
            "id": None,
            "subject_id": s.subject_id,
            "subject_db_id": s.id,
            "subject_name": s.name or s.subject_id,
            "no_assessment": True,
            "cycle_number": None,
            "visit_name": None,
            "assessment_date": None,
            "timepoint": "",
            "target_status": "",
            "target_reason": "",
            "non_target_status": "",
            "non_target_reason": "",
            "has_new_lesion": False,
            "new_lesion_text": "",
            "overall_status": "",
            "overall_reason": "",
            "effective_status": "",
            "effective_target_status": "",
            "effective_non_target_status": "",
            "manual_target_status": "",
            "manual_non_target_status": "",
            "manual_overall_status": "",
            "manual_has_new_lesion": False,
            "target_match": None,
            "non_target_match": None,
            "overall_match": None,
            "has_manual_data": False,
            "baseline_sum": None,
            "current_sum": None,
            "nadir_sum": None,
            "change_percent": None,
            "change_from_nadir_pct": None,
            "target_lesions": [],
            "non_target_lesions": []
        })

    return {
        "total_subjects": unique_subjects,
        "total_assessments": len(all_assessments),
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "no_human_count": no_human_count,
        "match_rate": match_rate,
        "status_distribution": status_dist,
        "status_counts": status_dist,
        "target_status_counts": target_dist,
        "non_target_status_counts": ntl_dist,
        "new_lesion_count": new_lesion_count,
        "response_rate": orr,
        "disease_control_rate": dcr,
        "average_change_percent": round(avg_change, 2),
        "recent_assessments": recent_data,
        "assessment_table": assessment_table,
        "batches": batch_list
    }
