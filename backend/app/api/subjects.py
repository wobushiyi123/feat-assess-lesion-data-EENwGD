"""受试者管理API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
import io
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.database import User, Subject, Assessment
from app.schemas.schemas import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter(prefix="/api/subjects", tags=["受试者"])


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    subject_data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建受试者"""
    existing = db.query(Subject).filter(
        Subject.subject_id == subject_data.subject_id,
        Subject.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="受试者ID已存在")

    data = subject_data.model_dump()
    data['user_id'] = current_user.id
    subject = Subject(**data)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    keyword: Optional[str] = Query(None, description="搜索关键字（ID或姓名）"),
    batch_id: Optional[int] = Query(None, description="导入批次ID（用于数据隔离）"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取受试者列表（仅返回当前用户的受试者；传 batch_id 时仅返回该批次内有评估的受试者）"""
    query = db.query(Subject).filter(Subject.user_id == current_user.id)

    if keyword:
        query = query.filter(
            or_(
                Subject.subject_id.contains(keyword),
                Subject.name.contains(keyword)
            )
        )

    # 按批次隔离：返回「该批次下存在评估记录的受试者」或「自身归属该批次的受试者」（含手动新增、可能尚无评估）
    if batch_id is not None:
        from sqlalchemy import distinct
        batch_subject_ids = db.query(Assessment.subject_id).filter(
            Assessment.batch_id == batch_id
        ).distinct().subquery()
        query = query.filter(
            or_(Subject.batch_id == batch_id, Subject.id.in_(batch_subject_ids))
        )

    subjects = query.order_by(Subject.created_at.desc()).offset(skip).limit(limit).all()
    return subjects


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    batch_id: Optional[int] = Query(None, description="导入批次ID（用于数据隔离，仅返回该批次的评估）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取受试者详情（传 batch_id 时仅返回该批次下的评估记录）"""
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id
    ).options(
        selectinload(Subject.assessments)
        .selectinload(Assessment.target_lesions),
        selectinload(Subject.assessments)
        .selectinload(Assessment.non_target_lesions),
        selectinload(Subject.assessments)
        .selectinload(Assessment.new_lesions)
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="受试者不存在")

    # 按批次过滤评估记录
    if batch_id is not None:
        subject.assessments = [a for a in subject.assessments if a.batch_id == batch_id]

    return subject


@router.get("/{subject_id}/export-query")
async def export_subject_query(
    subject_id: int,
    batch_id: Optional[int] = Query(None, description="导入批次ID（用于数据隔离）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """一键下发质疑：导出受试者信息 + 各周期系统判断结果 + 逐病灶基线/当期径线 + 新病灶信息。

    文件名为「{受试者编号}质疑下发.xlsx」，含 5 个 sheet：
      1) 受试者信息
      2) 疗效评估明细（靶/非靶/新病灶/总体 + 细化判断原因）
      3) 靶病灶明细（基线直径/当前直径/变化/器官分类/是否淋巴结）
      4) 非靶病灶明细（基线状态/当前状态/器官分类）
      5) 新病灶明细
    """
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id
    ).options(
        selectinload(Subject.assessments)
        .selectinload(Assessment.target_lesions),
        selectinload(Subject.assessments)
        .selectinload(Assessment.non_target_lesions),
        selectinload(Subject.assessments)
        .selectinload(Assessment.new_lesions),
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="受试者不存在")

    assessments = sorted(
        subject.assessments,
        key=lambda a: ((a.assessment_date or datetime.min).timestamp(), a.id or 0)
    )

    # 按批次过滤
    if batch_id is not None:
        assessments = [a for a in assessments if a.batch_id == batch_id]

    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法导出")

    wb = Workbook()

    # ===== Sheet 1: 受试者信息 =====
    ws_info = wb.active
    ws_info.title = "受试者信息"
    ws_info.append(["字段", "值"])
    info_rows = [
        ["受试者编号", subject.subject_id],
        ["姓名", subject.name],
        ["性别", subject.gender or ""],
        ["年龄", subject.age if subject.age is not None else ""],
        ["诊断", subject.diagnosis or ""],
        ["基线日期", subject.baseline_date.strftime("%Y-%m-%d") if subject.baseline_date else ""],
        ["评估周期数", len(assessments)],
        ["最新总体疗效", assessments[-1].overall_status if assessments else ""],
    ]
    for r in info_rows:
        ws_info.append(r)

    # ===== Sheet 2: 疗效评估明细 =====
    ws_eval = wb.create_sheet("疗效评估明细")
    ws_eval.append([
        "周期", "评估日期", "靶病灶评估", "非靶病灶评估", "新病灶", "总体疗效",
        "基线SLD(mm)", "当前SLD(mm)", "变化率(%)", "Nadir SLD(mm)", "较Nadir变化(%)",
        "靶病灶判断原因", "非靶病灶判断原因", "总体判断原因",
    ])
    for a in assessments:
        ws_eval.append([
            a.cycle_number,
            a.assessment_date.strftime("%Y-%m-%d") if a.assessment_date else "",
            a.target_status or "",
            a.non_target_status or "",
            "有" if a.has_new_lesion else "无",
            a.overall_status or "",
            round(a.baseline_sum or 0, 1),
            round(a.current_sum or 0, 1),
            round(a.change_percent or 0, 1),
            round(a.nadir_sum or 0, 1),
            round(a.change_from_nadir_pct or 0, 1),
            a.target_reason or "",
            a.non_target_reason or "",
            a.overall_reason or "",
        ])

    # ===== Sheet 3: 靶病灶明细 =====
    ws_tl = wb.create_sheet("靶病灶明细")
    ws_tl.append([
        "周期", "病灶编号", "名称(器官-描述)", "位置", "器官分类", "是否淋巴结",
        "基线直径(mm)", "当前直径(mm)", "变化(%)", "基线检查日期", "当前检查日期",
    ])
    for a in assessments:
        for tl in a.target_lesions:
            b = tl.baseline_size or 0.0
            c = tl.current_size or 0.0
            pct = ((c - b) / b * 100) if b else 0.0
            ws_tl.append([
                a.cycle_number, tl.lesion_id or "", tl.name or "", tl.location or "",
                tl.organ or "", "是" if tl.is_lymph_node else "否",
                round(b, 1), round(c, 1), round(pct, 1),
                tl.exam_date or "", tl.current_exam_date or "",
            ])

    # ===== Sheet 4: 非靶病灶明细 =====
    ws_ntl = wb.create_sheet("非靶病灶明细")
    ws_ntl.append([
        "周期", "病灶编号", "名称", "位置", "器官分类", "基线状态", "当前状态",
        "基线检查日期", "当前检查日期",
    ])
    for a in assessments:
        for ntl in a.non_target_lesions:
            ws_ntl.append([
                a.cycle_number, ntl.lesion_id or "", ntl.name or "", ntl.location or "",
                ntl.organ or "", ntl.baseline_status or "", ntl.status or "",
                ntl.exam_date or "", ntl.current_exam_date or "",
            ])

    # ===== Sheet 5: 新病灶明细 =====
    ws_nl = wb.create_sheet("新病灶明细")
    ws_nl.append(["周期", "病灶编号", "名称", "位置", "器官分类", "检查日期", "检查方法"])
    for a in assessments:
        for nl in a.new_lesions:
            ws_nl.append([
                a.cycle_number, nl.lesion_id or "", nl.name or "", nl.location or "",
                nl.organ or "", nl.exam_date or "", nl.exam_method or "",
            ])

    # 简单列宽自适应
    for ws in wb.worksheets:
        for col in ws.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 12), 70)

    output = io.BytesIO()
    wb.save(output)
    data = output.getvalue()

    filename = f"{subject.subject_id}质疑下发.xlsx"
    from urllib.parse import quote
    encoded = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"
    }
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    subject_data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新受试者信息"""
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="受试者不存在")

    update_data = subject_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(subject, key, value)

    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除受试者"""
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="受试者不存在")

    db.delete(subject)
    db.commit()
    return None