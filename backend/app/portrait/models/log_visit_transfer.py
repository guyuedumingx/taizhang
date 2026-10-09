"""
portrait 操作日志 + 家访 + 组员调换
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class OperationLog(Base):
    """操作日志 - 用户所有写操作留痕"""
    __tablename__ = "portrait_operation_logs"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    detail = Column(Text, nullable=True)
    ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=beijing_now)


class HomeVisitRecord(Base):
    """家访记录 - 组长对组员家访, 团队名称固定为「审核处理团队」

    PRD §7.1 (C1 阶段) 扩展字段:
      - co_visitor_user_id: 第二家访人 (双人员家访, 必填但 nullable 给旧数据兼容)
      - scan_file_path: 扫描件相对路径 (uploads/portrait/home_visits/{year}/{uuid}.{ext})
      - team_name: 固定 "审核处理团队", 后端兜底写
    """
    __tablename__ = "portrait_home_visit_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    visited_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visitor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    visit_year = Column(Integer, nullable=False)
    visit_time = Column(DateTime, nullable=False)
    visit_method = Column(String(20), nullable=False)
    visit_address = Column(String(500), nullable=True)
    visitor_info = Column(String(500), nullable=True)
    is_visited = Column(Boolean, default=False)

    visit_date = Column(Date, nullable=True)
    position = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    mobile = Column(String(20), nullable=True)
    home_phone = Column(String(20), nullable=True)

    family1_name = Column(String(100), nullable=True)
    family1_relation = Column(String(50), nullable=True)
    family1_contact = Column(String(50), nullable=True)
    family1_work_unit = Column(String(300), nullable=True)

    family2_name = Column(String(100), nullable=True)
    family2_relation = Column(String(50), nullable=True)
    family2_contact = Column(String(50), nullable=True)
    family2_work_unit = Column(String(300), nullable=True)

    feedback = Column(Text, nullable=True)

    # P6 家访审批流: 状态机字段 (集成指南 §5 雷区 6: portrait 独立 status String, 不复用台账 ApprovalStatus 枚举)
    status = Column(String(20), nullable=False, default="draft", index=True)
    current_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # C1 阶段新增 (PRD §7.1) — 双人员家访 + 扫描件 + 团队名称
    co_visitor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    scan_file_path = Column(String(500), nullable=True)
    team_name = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    visited_user = relationship("User", foreign_keys=[visited_user_id])
    visitor_user = relationship("User", foreign_keys=[visitor_user_id])
    current_approver = relationship("User", foreign_keys=[current_approver_id])
    co_visitor = relationship("User", foreign_keys=[co_visitor_user_id])


class GroupTransferHistory(Base):
    """组员调换历史 - leave_date IS NULL 表示当前仍在该组"""
    __tablename__ = "portrait_group_transfer_history"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ehr_no = Column(String(50), nullable=False, index=True)
    from_group = Column(String(100), nullable=True)
    to_group = Column(String(100), nullable=False)
    transfer_date = Column(DateTime, nullable=False)
    leave_date = Column(DateTime, nullable=True, index=True)
    operator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_ehr_no = Column(String(50), nullable=False)
    operator_name = Column(String(100), nullable=False)
    reason = Column(String(500), nullable=True)
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=beijing_now)

    user = relationship("User", foreign_keys=[user_id])
    operator = relationship("User", foreign_keys=[operator_user_id])