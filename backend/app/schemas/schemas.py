"""Pydantic数据校验模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# 用户相关
class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# 靶病灶
class TargetLesionBase(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    lesion_id: Optional[str] = None  # 靶病灶编号（EDC原始编号）
    organ: Optional[str] = None  # 器官分类（下拉枚举：淋巴结/肺/肝/骨/脑/肾上腺/腹膜后/盆腔/乳腺/皮下软组织/其他）
    is_lymph_node: bool = False  # 是否为淋巴结（影响 RECIST CR 阈值与径线选取）
    baseline_size: float = 0.0
    current_size: float = 0.0
    size_unit: str = "mm"  # 直径单位
    sum_diameter: float = 0.0  # 当前靶病灶直径和（随访）
    baseline_sum_diameter: float = 0.0  # 基线靶病灶直径和（与当前独立）
    baseline_date: Optional[datetime] = None
    is_checked: Optional[bool] = True  # 是否进行了检查？（基线）
    exam_date: Optional[str] = None  # 检查日期（基线）
    exam_method: Optional[str] = None  # 检查方法（基线）
    other_exam_method: Optional[str] = None  # 其他检查方法（基线）
    is_split_fused: Optional[str] = None  # 病灶是否发生了分裂或融合？（基线）
    split_fuse_detail: Optional[str] = None  # 分裂/融合详述（基线）
    unmeasurable_reason: Optional[str] = None  # 无法精确测量的原因（基线）
    # 当前(随访)检查信息
    current_is_checked: Optional[bool] = None  # 是否进行了检查？（当前）
    current_exam_date: Optional[str] = None  # 检查日期（当前）
    current_exam_method: Optional[str] = None  # 检查方法（当前）
    current_other_exam_method: Optional[str] = None  # 其他检查方法（当前）
    current_is_split_fused: Optional[str] = None  # 病灶是否发生了分裂或融合？（当前）
    current_split_fuse_detail: Optional[str] = None  # 分裂/融合详述（当前）
    notes: Optional[str] = None


class TargetLesionCreate(TargetLesionBase):
    pass


class TargetLesionResponse(TargetLesionBase):
    id: int
    change_percent: Optional[float] = None

    class Config:
        from_attributes = True


# 非靶病灶
class NonTargetLesionBase(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    lesion_id: Optional[str] = None  # 非靶病灶编号（EDC原始编号）
    organ: Optional[str] = None  # 器官分类（下拉枚举）
    is_lymph_node: bool = False  # 是否为淋巴结
    baseline_status: Optional[str] = "持续存在"  # 基线状态
    status: str  # 消失, 持续存在, 进展
    baseline_is_checked: Optional[bool] = None  # 是否进行了非靶病灶检查？（基线）
    current_is_checked: Optional[bool] = None  # 是否进行了非靶病灶检查？（当前）
    exam_date: Optional[str] = None  # 检查日期（基线）
    exam_method: Optional[str] = None  # 检查方法（基线）
    current_exam_date: Optional[str] = None  # 检查日期（当前）
    current_exam_method: Optional[str] = None  # 检查方法（当前）
    notes: Optional[str] = None


class NonTargetLesionCreate(NonTargetLesionBase):
    pass


class NonTargetLesionResponse(NonTargetLesionBase):
    id: int

    class Config:
        from_attributes = True


# 新病灶
class NewLesionBase(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    lesion_id: Optional[str] = None  # 新病灶编号（EDC原始编号）
    organ: Optional[str] = None  # 器官分类（下拉枚举）
    is_lymph_node: bool = False  # 是否为淋巴结
    exam_date: Optional[str] = None  # 检查日期
    exam_method: Optional[str] = None  # 检查方法
    other_exam_method: Optional[str] = None  # 其他检查方法
    notes: Optional[str] = None


class NewLesionResponse(NewLesionBase):
    id: int

    class Config:
        from_attributes = True


class NewLesionCreate(NewLesionBase):
    pass


# 评估记录
class AssessmentBase(BaseModel):
    assessment_date: Optional[datetime] = None
    cycle_number: int = 1
    visit_name: Optional[str] = None  # EDC 原始访视名称，如"肿瘤疗效评估（RECIST1.1）#2（第8周±7天）"
    has_new_lesion: bool = False
    tumor_marker_normal: bool = True
    notes: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    subject_id: int
    batch_id: Optional[int] = None
    target_lesions: List[TargetLesionCreate] = []
    non_target_lesions: List[NonTargetLesionCreate] = []
    new_lesions: List[NewLesionCreate] = []


class AssessmentResponse(AssessmentBase):
    id: int
    subject_id: int
    batch_id: Optional[int] = None
    target_status: Optional[str] = None
    target_reason: Optional[str] = None
    non_target_status: Optional[str] = None
    non_target_reason: Optional[str] = None
    overall_status: Optional[str] = None
    overall_reason: Optional[str] = None
    manual_target_status: Optional[str] = None
    manual_non_target_status: Optional[str] = None
    manual_overall_status: Optional[str] = None
    manual_has_new_lesion: bool = False
    baseline_sum: float
    current_sum: float
    nadir_sum: float
    change_percent: float
    change_from_nadir_pct: Optional[float] = None
    absolute_change: float
    ai_prediction: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    target_lesions: List[TargetLesionResponse] = []
    non_target_lesions: List[NonTargetLesionResponse] = []
    new_lesions: List[NewLesionResponse] = []

    class Config:
        from_attributes = True


# 受试者
class SubjectBase(BaseModel):
    subject_id: str
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    baseline_date: Optional[datetime] = None
    notes: Optional[str] = None
    batch_id: Optional[int] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    baseline_date: Optional[datetime] = None
    notes: Optional[str] = None


class SubjectResponse(SubjectBase):
    id: int
    batch_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    assessments: List[AssessmentResponse] = []

    class Config:
        from_attributes = True


# 评估请求
class AssessmentRequest(BaseModel):
    """评估请求 - 直接进行评估计算"""
    target_lesions: List[Dict[str, Any]]
    non_target_lesions: List[Dict[str, Any]]
    has_new_lesion: bool = False
    tumor_marker_normal: bool = True


class AssessmentResult(BaseModel):
    """评估结果"""
    target_status: str
    target_reason: str
    non_target_status: str
    non_target_reason: str
    overall_status: str
    overall_reason: str
    baseline_sum: float
    current_sum: float
    change_percent: float
    absolute_change: float
    ai_prediction: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    recommendations: List[str] = []


# 智能分析
class TrendAnalysis(BaseModel):
    """趋势分析结果"""
    subject_id: int
    trend_direction: str  # improving, stable, worsening
    predicted_next_status: str
    confidence: float
    analysis_summary: str
    historical_data: List[Dict[str, Any]]


class StatisticsResponse(BaseModel):
    """统计响应"""
    total_subjects: int
    total_assessments: int
    status_distribution: Dict[str, int]
    response_rate: float
    average_change_percent: float
    disease_control_rate: float
    recent_assessments: List[Dict[str, Any]]