from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON
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
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    
    # 台账元字段（默认值）
    default_ledger_name = Column(String, nullable=True)
    default_description = Column(Text, nullable=True)
    default_status = Column(String, nullable=True, default="draft")
    default_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    default_metadata = Column(JSON, nullable=True)  # 可以存储其他默认元数据
    
    # 默认工作流
    default_workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    
    # 外键
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    fields = relationship("Field", back_populates="template", cascade="all, delete-orphan")
    ledgers = relationship("Ledger", back_populates="template")
    creator = relationship("User", foreign_keys=[created_by_id])
    updater = relationship("User", foreign_keys=[updated_by_id])
    default_team = relationship("Team", foreign_keys=[default_team_id])
    default_workflow = relationship("Workflow", foreign_keys=[default_workflow_id])
    workflow = relationship(
        "Workflow",
        back_populates="templates",
        primaryjoin="and_(Template.workflow_id==Workflow.id, Template.workflow_id!=None)",
        foreign_keys=[workflow_id]
    ) 