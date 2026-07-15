"""评估相关API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import datetime, timezone
import logging
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.database import User, Subject, Assessment, TargetLesion, NonTargetLesion, NewLesion
from app.schemas.schemas import AssessmentCreate, AssessmentResponse, AssessmentRequest, AssessmentResult
from app.services.recist_engine import RecistEngine
from app.services.intelligent_analyzer import IntelligentAnalyzer

router = APIRouter(prefix="/api/assessments", tags=["评估"])
logger = logging.getLogger(__name__)


@router.post("/calculate", response_model=AssessmentResult)
async def calculate_assessment(
    request: AssessmentRequest,
    current_user: User = Depends(get_current_user)
):
    """实时计算评估结果（不保存）"""
    result = RecistEngine.perform_assessment(
        target_lesions=request.target_lesions,
        non_target_lesions=request.non_target_lesions,
        has_new_lesion=request.has_new_lesion,
        tumor_marker_normal=request.tumor_marker_normal
    )

    # 计算风险评分
    risk_score = IntelligentAnalyzer.calculate_risk_score({
        "change_percent": result.change_percent,
        "has_new_lesion": request.has_new_lesion,
        "non_target_status": result.non_target_status,
        "tumor_marker_normal": request.tumor_marker_normal
    })

    # 生成建议
    recommendations = IntelligentAnalyzer.generate_recommendations(
        current_status=result.overall_status,
        risk_score=risk_score,
        trend={}
    )

    return AssessmentResult(
        target_status=result.target_status,
        target_reason=result.target_reason,
        non_target_status=result.non_target_status,
        non_target_reason=result.non_target_reason,
        overall_status=result.overall_status,
        overall_reason=result.overall_reason,
        baseline_sum=result.baseline_sum,
        current_sum=result.current_sum,
        change_percent=result.change_percent,
        absolute_change=result.absolute_change,
        risk_score=risk_score,
        recommendations=recommendations
    )


def _recompute_assessment(assessment: Assessment, db: Session) -> None:
    """依据当前病灶明细重算 Assessment 的 SLD 汇总 / Nadir / 疗效 / 风险并写回。

    - Nadir 取「历史各期 current_sum 与当前期 current_sum」的最小值（含当前），
      符合 RECIST 1.1「历史最低点」定义，避免 Nadir 高于当前期的业务悖论。
    - 新病灶存在时 has_new_lesion=True，整体疗效一票否决为 PD（最高优先级）。
    """
    target_lesions = db.query(TargetLesion).filter(TargetLesion.assessment_id == assessment.id).all()
    non_target_lesions = db.query(NonTargetLesion).filter(NonTargetLesion.assessment_id == assessment.id).all()
    new_lesions = db.query(NewLesion).filter(NewLesion.assessment_id == assessment.id).all()
    has_new_lesion = len(new_lesions) > 0

    subject_id = assessment.subject_id
    subject_has_target = db.query(TargetLesion).join(Assessment).filter(
        Assessment.subject_id == subject_id).first() is not None
    subject_has_ntl = db.query(NonTargetLesion).join(Assessment).filter(
        Assessment.subject_id == subject_id).first() is not None

    tl_dicts = [{"baseline_size": l.baseline_size or 0, "current_size": l.current_size or 0}
                for l in target_lesions]
    ntl_dicts = [{"status": l.status, "baseline_status": l.baseline_status}
                 for l in non_target_lesions]

    # 当前期 SLD，纳入 Nadir 计算
    current_sum = sum((l.current_size or 0) for l in target_lesions)
    # 历史（其它期）current_sum
    history = db.query(Assessment).filter(
        Assessment.subject_id == subject_id,
        Assessment.id != assessment.id
    ).order_by(Assessment.cycle_number).all()
    history_sums = [h.current_sum for h in history if h.current_sum]
    all_sums = history_sums + ([current_sum] if current_sum else [])
    nadir_sld = min(all_sums) if all_sums else None

    tumor_marker_normal = assessment.tumor_marker_normal if assessment.tumor_marker_normal is not None else True

    result = RecistEngine.perform_assessment(
        target_lesions=tl_dicts,
        non_target_lesions=ntl_dicts,
        has_new_lesion=has_new_lesion,
        tumor_marker_normal=tumor_marker_normal,
        nadir_sum=nadir_sld,
        target_not_applicable=not subject_has_target,
        non_target_not_applicable=not subject_has_ntl,
    )

    risk_score = IntelligentAnalyzer.calculate_risk_score({
        "change_percent": result.change_percent,
        "has_new_lesion": has_new_lesion,
        "non_target_status": result.non_target_status,
        "tumor_marker_normal": tumor_marker_normal,
    })
    history_data = [
        {"cycle_number": a.cycle_number, "change_percent": a.change_percent, "overall_status": a.overall_status}
        for a in history
    ]
    history_data.append({
        "cycle_number": assessment.cycle_number,
        "change_percent": result.change_percent,
        "overall_status": result.overall_status
    })
    prediction = IntelligentAnalyzer.predict_next_status(history_data)
    prediction["recommendations"] = IntelligentAnalyzer.generate_recommendations(
        current_status=result.overall_status, risk_score=risk_score, trend={}
    )

    assessment.has_new_lesion = has_new_lesion
    assessment.target_status = result.target_status
    assessment.target_reason = result.target_reason
    assessment.non_target_status = result.non_target_status
    assessment.non_target_reason = result.non_target_reason
    assessment.overall_status = result.overall_status
    assessment.overall_reason = result.overall_reason
    assessment.baseline_sum = result.baseline_sum
    assessment.current_sum = result.current_sum
    assessment.change_percent = result.change_percent
    assessment.nadir_sum = result.nadir_sum
    assessment.change_from_nadir_pct = result.change_from_nadir_pct
    assessment.absolute_change = result.absolute_change
    assessment.risk_score = risk_score
    assessment.ai_prediction = prediction
    db.add(assessment)


def _get_baseline_assessment(db: Session, subject_id: int) -> Assessment | None:
    """返回该受试者基线期评估（按评估日期升序、其次 id 升序的第一条）。"""
    return db.query(Assessment).filter(Assessment.subject_id == subject_id) \
        .order_by(Assessment.assessment_date, Assessment.id).first()


def _assert_lesion_id_inherits_baseline(db: Session, assessment: Assessment, lesion_type: str, lesion_id) -> None:
    """纵向防呆：随访期新增靶/非靶病灶时，编号必须继承基线期同类型病灶编号。

    - 基线期自身、或无可比对的基线时放行；
    - 否则若编号不在基线同类型编号集合内，拦截（新发肿瘤应走「新病灶」页签）。
    """
    if not lesion_id:
        return
    baseline = _get_baseline_assessment(db, assessment.subject_id)
    if baseline is None or baseline.id == assessment.id:
        return
    if lesion_type == 'target':
        rows = db.query(TargetLesion.lesion_id).filter(TargetLesion.assessment_id == baseline.id).all()
    else:
        rows = db.query(NonTargetLesion.lesion_id).filter(NonTargetLesion.assessment_id == baseline.id).all()
    base_ids = [r[0] for r in rows if r[0]]
    if lesion_id not in base_ids:
        label = '靶' if lesion_type == 'target' else '非靶'
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"随访期{label}病灶编号必须继承基线期编号（基线编号：{', '.join(base_ids) or '无'}）。新发肿瘤请使用「新病灶」页签新增。"
        )


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建评估记录"""
    subject = db.query(Subject).filter(Subject.id == assessment_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="受试者不存在")

    # assessment_date：优先取病灶实际检查日期，其次取导入/创建时刻（前端手动新增病灶时不传该字段）
    def _to_dt(v):
        if not v:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except (ValueError, TypeError):
                return None
        return None

    _assessment_date = _to_dt(assessment_data.assessment_date)
    if not _assessment_date:
        _assessment_date = (
            _to_dt(next((l.current_exam_date for l in assessment_data.target_lesions if l.current_exam_date), None))
            or _to_dt(next((l.exam_date for l in assessment_data.target_lesions if l.exam_date), None))
            or _to_dt(next((l.exam_date for l in assessment_data.non_target_lesions if l.exam_date), None))
            or _to_dt(next((l.exam_date for l in assessment_data.new_lesions if l.exam_date), None))
            or datetime.now(timezone.utc)
        )

    assessment = Assessment(
        subject_id=subject.id,
        batch_id=assessment_data.batch_id,
        assessment_date=_assessment_date,
        cycle_number=assessment_data.cycle_number,
        has_new_lesion=assessment_data.has_new_lesion,
        tumor_marker_normal=assessment_data.tumor_marker_normal,
        raw_data={
            "target_lesions": [l.model_dump() for l in assessment_data.target_lesions],
            "non_target_lesions": [l.model_dump() for l in assessment_data.non_target_lesions],
            "new_lesions": [l.model_dump() for l in assessment_data.new_lesions],
        },
    )
    db.add(assessment)
    db.flush()

    for lesion in assessment_data.target_lesions:
        db.add(TargetLesion(assessment_id=assessment.id, **lesion.model_dump()))
    for lesion in assessment_data.non_target_lesions:
        db.add(NonTargetLesion(assessment_id=assessment.id, **lesion.model_dump()))
    for lesion in assessment_data.new_lesions:
        db.add(NewLesion(assessment_id=assessment.id, **lesion.model_dump()))

    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("创建评估时重算评估结果失败（不影响保存）: %s", exc)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/algorithm")
async def get_recist_algorithm():
    """
    获取 RECIST 1.1 评估算法的完整说明

    返回算法版本、判定阈值、决策规则、优先级等结构化信息，
    用于前端展示或 API 文档。
    """
    return RecistEngine.get_algorithm_summary()


@router.get("/subject/{subject_id}", response_model=List[AssessmentResponse])
async def list_subject_assessments(
    subject_id: int,
    batch_id: Optional[int] = Query(None, description="导入批次ID（用于数据隔离）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取受试者的所有评估记录（传 batch_id 时仅返回该批次的评估）"""
    query = db.query(Assessment).filter(
        Assessment.subject_id == subject_id
    )
    if batch_id is not None:
        query = query.filter(Assessment.batch_id == batch_id)
    assessments = query.options(
        selectinload(Assessment.target_lesions),
        selectinload(Assessment.non_target_lesions),
        selectinload(Assessment.new_lesions)
    ).order_by(Assessment.cycle_number).all()
    return assessments


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取评估详情"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).options(
        selectinload(Assessment.target_lesions),
        selectinload(Assessment.non_target_lesions),
        selectinload(Assessment.new_lesions)
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    return assessment


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除评估记录"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")

    db.delete(assessment)
    db.commit()
    return None


# ========== 病灶增删改 API ==========

from pydantic import BaseModel
from fastapi import Body


class TargetLesionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    description: str | None = None
    lesion_id: str | None = None
    baseline_size: float | None = None
    current_size: float | None = None
    size_unit: str | None = None
    sum_diameter: float | None = None
    is_checked: bool | None = None
    exam_date: str | None = None
    exam_method: str | None = None
    other_exam_method: str | None = None
    is_split_fused: str | None = None
    unmeasurable_reason: str | None = None
    current_is_checked: bool | None = None
    current_exam_date: str | None = None
    current_exam_method: str | None = None
    current_other_exam_method: str | None = None
    current_is_split_fused: str | None = None
    notes: str | None = None
    organ: str | None = None  # 器官分类（下拉枚举）
    is_lymph_node: bool | None = None  # 是否为淋巴结


class NonTargetLesionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    description: str | None = None
    lesion_id: str | None = None
    baseline_status: str | None = None
    status: str | None = None
    baseline_is_checked: bool | None = None
    current_is_checked: bool | None = None
    exam_date: str | None = None
    exam_method: str | None = None
    current_exam_date: str | None = None
    current_exam_method: str | None = None
    notes: str | None = None
    organ: str | None = None  # 器官分类（下拉枚举）
    is_lymph_node: bool | None = None  # 是否为淋巴结


class NewLesionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    description: str | None = None
    lesion_id: str | None = None
    exam_date: str | None = None
    exam_method: str | None = None
    other_exam_method: str | None = None
    notes: str | None = None
    organ: str | None = None  # 器官分类（下拉枚举）
    is_lymph_node: bool | None = None  # 是否为淋巴结


@router.put("/{assessment_id}/target-lesions/{lesion_id}")
async def update_target_lesion(
    assessment_id: int,
    lesion_id: int,
    data: TargetLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新靶病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    lesion = db.query(TargetLesion).filter(
        TargetLesion.id == lesion_id, TargetLesion.assessment_id == assessment_id
    ).first()
    if not lesion:
        raise HTTPException(status_code=404, detail="靶病灶记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lesion, key, value)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("更新靶病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "靶病灶已更新"}


@router.put("/{assessment_id}/non-target-lesions/{lesion_id}")
async def update_non_target_lesion(
    assessment_id: int,
    lesion_id: int,
    data: NonTargetLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新非靶病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    lesion = db.query(NonTargetLesion).filter(
        NonTargetLesion.id == lesion_id, NonTargetLesion.assessment_id == assessment_id
    ).first()
    if not lesion:
        raise HTTPException(status_code=404, detail="非靶病灶记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lesion, key, value)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("更新非靶病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "非靶病灶已更新"}


@router.put("/{assessment_id}/new-lesions/{lesion_id}")
async def update_new_lesion(
    assessment_id: int,
    lesion_id: int,
    data: NewLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新新病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    lesion = db.query(NewLesion).filter(
        NewLesion.id == lesion_id, NewLesion.assessment_id == assessment_id
    ).first()
    if not lesion:
        raise HTTPException(status_code=404, detail="新病灶记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lesion, key, value)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("更新新病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "新病灶已更新"}


def _cleanup_empty_assessment(assessment: Assessment, db: Session) -> None:
    """若评估记录下已无任何病灶（靶+非靶+新），则删除该评估记录。"""
    remaining = (
        db.query(TargetLesion).filter(TargetLesion.assessment_id == assessment.id).count()
        + db.query(NonTargetLesion).filter(NonTargetLesion.assessment_id == assessment.id).count()
        + db.query(NewLesion).filter(NewLesion.assessment_id == assessment.id).count()
    )
    if remaining == 0:
        logger.info("assessment %d 无残留病灶，自动删除评估记录", assessment.id)
        db.delete(assessment)


@router.delete("/{assessment_id}/target-lesions/{lesion_id}")
async def delete_target_lesion(
    assessment_id: int,
    lesion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除靶病灶"""
    try:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="评估记录不存在")
        lesion = db.query(TargetLesion).filter(
            TargetLesion.id == lesion_id, TargetLesion.assessment_id == assessment_id
        ).first()
        if not lesion:
            raise HTTPException(status_code=404, detail="靶病灶记录不存在")
        db.delete(lesion)
        db.flush()
        # 重算（允许失败，不影响删除）
        try:
            _recompute_assessment(assessment, db)
        except Exception as e:
            logger.warning("重算 assessment %d 失败（不影响删除）: %s", assessment_id, e)
        # 若该评估下无任何病灶了，一并清理评估
        _cleanup_empty_assessment(assessment, db)
        db.commit()
        return {"message": "靶病灶已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("删除靶病灶失败 assessment=%d lesion=%d: %s", assessment_id, lesion_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除靶病灶失败: {str(e)}")


@router.delete("/{assessment_id}/non-target-lesions/{lesion_id}")
async def delete_non_target_lesion(
    assessment_id: int,
    lesion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除非靶病灶"""
    try:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="评估记录不存在")
        lesion = db.query(NonTargetLesion).filter(
            NonTargetLesion.id == lesion_id, NonTargetLesion.assessment_id == assessment_id
        ).first()
        if not lesion:
            raise HTTPException(status_code=404, detail="非靶病灶记录不存在")
        db.delete(lesion)
        db.flush()
        try:
            _recompute_assessment(assessment, db)
        except Exception as e:
            logger.warning("重算 assessment %d 失败（不影响删除）: %s", assessment_id, e)
        _cleanup_empty_assessment(assessment, db)
        db.commit()
        return {"message": "非靶病灶已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("删除非靶病灶失败 assessment=%d lesion=%d: %s", assessment_id, lesion_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除非靶病灶失败: {str(e)}")


@router.delete("/{assessment_id}/new-lesions/{lesion_id}")
async def delete_new_lesion(
    assessment_id: int,
    lesion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除新病灶"""
    try:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="评估记录不存在")
        lesion = db.query(NewLesion).filter(
            NewLesion.id == lesion_id, NewLesion.assessment_id == assessment_id
        ).first()
        if not lesion:
            raise HTTPException(status_code=404, detail="新病灶记录不存在")
        db.delete(lesion)
        db.flush()
        try:
            _recompute_assessment(assessment, db)
        except Exception as e:
            logger.warning("重算 assessment %d 失败（不影响删除）: %s", assessment_id, e)
        _cleanup_empty_assessment(assessment, db)
        db.commit()
        return {"message": "新病灶已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("删除新病灶失败 assessment=%d lesion=%d: %s", assessment_id, lesion_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除新病灶失败: {str(e)}")


@router.post("/{assessment_id}/target-lesions", status_code=status.HTTP_201_CREATED)
async def create_target_lesion(
    assessment_id: int,
    data: TargetLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """新增靶病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    _assert_lesion_id_inherits_baseline(db, assessment, 'target', data.lesion_id)
    payload = data.model_dump(exclude_unset=True)
    payload["assessment_id"] = assessment_id
    if not payload.get("name"):
        payload["name"] = payload.get("location") or "未命名靶病灶"
    lesion = TargetLesion(**payload)
    db.add(lesion)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("新增靶病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "靶病灶已添加"}


@router.post("/{assessment_id}/non-target-lesions", status_code=status.HTTP_201_CREATED)
async def create_non_target_lesion(
    assessment_id: int,
    data: NonTargetLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """新增非靶病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    _assert_lesion_id_inherits_baseline(db, assessment, 'nonTarget', data.lesion_id)
    payload = data.model_dump(exclude_unset=True)
    payload["assessment_id"] = assessment_id
    if not payload.get("name"):
        payload["name"] = payload.get("location") or "未命名非靶病灶"
    lesion = NonTargetLesion(**payload)
    db.add(lesion)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("新增非靶病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "非靶病灶已添加"}


@router.post("/{assessment_id}/new-lesions", status_code=status.HTTP_201_CREATED)
async def create_new_lesion(
    assessment_id: int,
    data: NewLesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """新增新病灶"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    payload = data.model_dump(exclude_unset=True)
    payload["assessment_id"] = assessment_id
    if not payload.get("name"):
        payload["name"] = payload.get("location") or "未命名新病灶"
    lesion = NewLesion(**payload)
    db.add(lesion)
    db.flush()
    try:
        _recompute_assessment(assessment, db)
    except Exception as exc:
        logger.warning("新增新病灶时重算评估结果失败: %s", exc)
    db.commit()
    db.refresh(lesion)
    return {"id": lesion.id, "message": "新病灶已添加"}