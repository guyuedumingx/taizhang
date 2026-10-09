"""
portrait 培训记录模型 (PRD §10.3 占位预留)

字段参考 PRD §10.3 培训记录:
  - 培训名、培训时间、培训类型、培训机构、证书编号、有效期

注意:
  - v2.0 第一版仅占位 (员工 D2 可见, 管理员导入入口预留)
  - 完整功能 (登记 / 审批 / 矩阵视图) 留待后续版本
  - ehr_id 字段存原始 7 位数字, 不做 FK 约束 (避免与 users.ehr_id 类型变更冲突)
"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class TrainingRecord(Base):
    """培训记录 - 个人培训历史占位表

    表名: portrait_training_records
    """
    __tablename__ = "portrait_training_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ehr_id = Column(String(7), nullable=False, index=True)  # 冗余, 方便查询/导出

    training_name = Column(String(128), nullable=False)
    training_at = Column(DateTime, nullable=False, index=True)
    training_type = Column(String(32), nullable=False)  # 内部/外部/线上/线下等
    institution = Column(String(128), nullable=False)
    certificate_no = Column(String(64), nullable=True)
    valid_until = Column(Date, nullable=True)

    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)