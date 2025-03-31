from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Ledger(Base):
    __tablename__ = "ledgers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft, active, completed
    
    # 审核状态
    approval_status = Column(String, nullable=False, default="pending")  # pending, approved, rejected
    current_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 外键
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    
    # 数据，存储为JSON
    data = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)  # 提交时间
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 最终审批时间
    
    # 关系
    team = relationship("Team", back_populates="ledgers")
    template = relationship("Template", back_populates="ledgers")
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_ledgers")
    updater = relationship("User", foreign_keys=[updated_by_id], back_populates="updated_ledgers")
    current_approver = relationship("User", foreign_keys=[current_approver_id])
    field_values = relationship("FieldValue", back_populates="ledger", cascade="all, delete-orphan")
    # workflow = relationship("Workflow", foreign_keys=[workflow_id])
    workflow_instance = relationship("WorkflowInstance", back_populates="ledger", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="ledger", cascade="all, delete-orphan") 