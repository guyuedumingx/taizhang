from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    department = Column(String, nullable=False)
    is_system = Column(Boolean, default=False)
    
    # 台账类型
    type = Column(String, nullable=False, default="standard")  # standard, no_rejection, auto_approval
    require_approval = Column(Boolean, default=True)  # 是否需要审批流程
    
    # 外键
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    default_workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)  # 默认工作流
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    fields = relationship("Field", back_populates="template", cascade="all, delete-orphan")
    ledgers = relationship("Ledger", back_populates="template")
    creator = relationship("User", foreign_keys=[created_by_id])
    updater = relationship("User", foreign_keys=[updated_by_id])
    default_workflow = relationship("Workflow", foreign_keys=[default_workflow_id])
    workflows = relationship("Workflow", back_populates="template", foreign_keys="Workflow.template_id") 