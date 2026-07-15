"""数据库模型定义"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="user")  # admin, doctor, user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ImportBatch(Base):
    """导入批次表 - 记录每次Excel导入"""
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    import_time = Column(DateTime, default=datetime.now)
    total_assessments = Column(Integer, default=0)
    subjects_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    assessments = relationship("Assessment", back_populates="batch")


class Subject(Base):
    """受试者表"""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(String(50), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    gender = Column(String(10))
    age = Column(Integer)
    diagnosis = Column(String(200))
    baseline_date = Column(DateTime)
    notes = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True, index=True)  # 手动新增受试者归属的批次（导入数据靠 Assessment.batch_id 隔离）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    assessments = relationship("Assessment", back_populates="subject", cascade="all, delete-orphan")


class Assessment(Base):
    """评估记录表"""
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    assessment_date = Column(DateTime, nullable=False)
    cycle_number = Column(Integer, default=1)
    visit_name = Column(String(200))  # EDC 原始访视名称，如"肿瘤疗效评估（RECIST1.1）#2（第8周±7天）"

    # 评估结果（自动计算）
    target_status = Column(String(20))  # CR, PR, SD, PD, NE, Non-CR/Non-PD
    target_reason = Column(Text)
    non_target_status = Column(String(20))  # CR, Non-CR/Non-PD, PD, NE
    non_target_reason = Column(Text)
    overall_status = Column(String(20))
    overall_reason = Column(Text)

    # 人工评估结果（用于自动↔人工一致性比对）
    manual_target_status = Column(String(20))
    manual_non_target_status = Column(String(20))
    manual_overall_status = Column(String(20))
    manual_has_new_lesion = Column(Boolean, default=False)

    # 数值指标
    baseline_sum = Column(Float, default=0.0)
    current_sum = Column(Float, default=0.0)
    nadir_sum = Column(Float, default=0.0)  # 历史最低 SLD（用于多周期 PD 判定）
    change_percent = Column(Float, default=0.0)
    change_from_nadir_pct = Column(Float, nullable=True)  # 较最低点变化率
    absolute_change = Column(Float, default=0.0)

    # 标志
    has_new_lesion = Column(Boolean, default=False)
    tumor_marker_normal = Column(Boolean, default=True)

    # 备注
    notes = Column(Text)

    # 智能分析结果
    ai_prediction = Column(JSON)  # AI预测结果
    risk_score = Column(Float)  # 风险评分

    # 完整数据快照
    raw_data = Column(JSON)

    # 导入批次
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    subject = relationship("Subject", back_populates="assessments")
    batch = relationship("ImportBatch", back_populates="assessments")
    target_lesions = relationship("TargetLesion", back_populates="assessment", cascade="all, delete-orphan")
    non_target_lesions = relationship("NonTargetLesion", back_populates="assessment", cascade="all, delete-orphan")
    new_lesions = relationship("NewLesion", back_populates="assessment", cascade="all, delete-orphan")


class TargetLesion(Base):
    """靶病灶表"""
    __tablename__ = "target_lesions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)

    # 基本信息
    name = Column(String(100), nullable=False)  # 器官 - 器官具体描述
    location = Column(String(100))  # 病灶所在器官
    description = Column(Text)  # 病灶所在器官具体描述
    lesion_id = Column(String(50))  # 靶病灶编号（EDC原始编号）
    organ = Column(String(50))  # 器官分类（下拉：淋巴结/肺/肝/骨/脑/肾上腺/腹膜后/盆腔/乳腺/皮下软组织/其他）
    is_lymph_node = Column(Boolean, default=False)  # 是否为淋巴结（影响 RECIST CR 阈值与径线选取）

    # 尺寸信息
    baseline_size = Column(Float, default=0.0)  # 基线最长直径
    current_size = Column(Float, default=0.0)   # 当前最长直径
    size_unit = Column(String(20), default="mm")  # 直径单位（mm等）
    sum_diameter = Column(Float, default=0.0)    # 当前靶病灶直径和（随访）
    baseline_sum_diameter = Column(Float, default=0.0)  # 基线靶病灶直径和（与当前独立存储）
    baseline_date = Column(DateTime)

    # 检查信息（基线）
    is_checked = Column(Boolean, default=True)  # 是否进行了检查？（基线）
    exam_date = Column(String(30))  # 检查日期（基线）
    exam_method = Column(String(100))  # 检查方法（基线）
    other_exam_method = Column(String(100))  # 其他检查方法（基线）

    # 分裂/融合/测量异常（基线）
    is_split_fused = Column(String(20))  # 病灶是否发生了分裂或融合？（基线，是/否/未知）
    split_fuse_detail = Column(Text)  # 如分裂或融合，请详述（基线）
    unmeasurable_reason = Column(Text)  # 无法精确测量的原因（基线）

    # 检查信息（当前 / 随访）
    current_is_checked = Column(Boolean)  # 是否进行了检查？（当前）
    current_exam_date = Column(String(30))  # 检查日期（当前）
    current_exam_method = Column(String(100))  # 检查方法（当前）
    current_other_exam_method = Column(String(100))  # 其他检查方法（当前）

    # 分裂/融合/测量异常（当前 / 随访）
    current_is_split_fused = Column(String(20))  # 病灶是否发生了分裂或融合？（当前，是/否/未知）
    current_split_fuse_detail = Column(Text)  # 如分裂或融合，请详述（当前）

    notes = Column(Text)

    assessment = relationship("Assessment", back_populates="target_lesions")


class NonTargetLesion(Base):
    """非靶病灶表"""
    __tablename__ = "non_target_lesions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)

    # 基本信息
    name = Column(String(100), nullable=False)
    location = Column(String(100))  # 病灶所在器官
    description = Column(Text)  # 病灶所在器官具体描述
    lesion_id = Column(String(50))  # 非靶病灶编号（EDC原始编号）
    organ = Column(String(50))  # 器官分类（下拉：淋巴结/肺/肝/骨/脑/肾上腺/腹膜后/盆腔/乳腺/皮下软组织/其他）
    is_lymph_node = Column(Boolean, default=False)  # 是否为淋巴结（影响 RECIST CR 阈值与径线选取）

    # 状态
    baseline_status = Column(String(20), default="持续存在")  # 基线状态（默认存在）
    status = Column(String(20))  # 消失, 持续存在, 进展

    # 检查标志
    baseline_is_checked = Column(Boolean, default=True)  # 是否进行了非靶病灶检查？（基线）
    current_is_checked = Column(Boolean)  # 是否进行了非靶病灶检查？（当前）

    # 检查信息（基线）
    exam_date = Column(String(30))  # 检查日期（基线）
    exam_method = Column(String(100))  # 检查方法（基线）

    # 检查信息（当前 / 随访）
    current_exam_date = Column(String(30))  # 检查日期（当前）
    current_exam_method = Column(String(100))  # 检查方法（当前）

    notes = Column(Text)

    assessment = relationship("Assessment", back_populates="non_target_lesions")


class NewLesion(Base):
    """新病灶表"""
    __tablename__ = "new_lesions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)

    # 基本信息
    name = Column(String(100), nullable=False)
    location = Column(String(100))  # 病灶所在器官
    description = Column(Text)  # 病灶所在器官具体描述
    lesion_id = Column(String(50))  # 新病灶编号（EDC原始编号）
    organ = Column(String(50))  # 器官分类（下拉：淋巴结/肺/肝/骨/脑/肾上腺/腹膜后/盆腔/乳腺/皮下软组织/其他）
    is_lymph_node = Column(Boolean, default=False)  # 是否为淋巴结

    # 检查信息
    exam_date = Column(String(30))  # 检查日期
    exam_method = Column(String(100))  # 检查方法
    other_exam_method = Column(String(100))  # 其他检查方法

    notes = Column(Text)

    assessment = relationship("Assessment", back_populates="new_lesions")


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    action = Column(String(50))
    target_type = Column(String(50))
    target_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())