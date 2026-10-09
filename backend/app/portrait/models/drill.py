"""
portrait 消防演练模型 (PRD §10.2 F2-F4, §14.1)
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class DrillRecord(Base):
    """消防演练活动主表 (F2 演练登记 / F3 批量导入 / F4 矩阵)"""
    __tablename__ = "portrait_drill_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_date = Column(Date, nullable=False, index=True)
    drill_type = Column(String(32), nullable=False)  # 演练/培训/应急疏散
    location = Column(String(128), nullable=False)
    duration_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class DrillParticipant(Base):
    """消防演练参与人员 (N:M, drill_id × ehr_id 唯一)"""
    __tablename__ = "portrait_drill_participants"
    __table_args__ = (
        UniqueConstraint("drill_id", "ehr_id", name="uq_drill_participant"),
        *PORTRAIT_TABLE_KWARGS,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    drill_id = Column(Integer, ForeignKey("portrait_drill_records.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ehr_id = Column(String(7), nullable=False, index=True)  # 冗余
    name = Column(String(64), nullable=False)  # 冗余, 方便矩阵/导出
    participated = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=beijing_now)