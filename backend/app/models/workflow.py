from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Text, JSON, Enum, Table, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from typing import List, Optional

from app.db.session import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# 审核状态枚举
class ApprovalStatus(str, Enum):
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    CANCELLED = "cancelled" # 已取消
    DRAFT = "draft" # 草稿

# 工作流节点与审批人关联表
workflow_node_approvers = Table(
    "workflow_node_approvers",
    Base.metadata,
    Column("workflow_node_id", Integer, ForeignKey("workflow_nodes.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)

# 工作流模型
class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    instances = relationship("WorkflowInstance", back_populates="workflow")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Workflow {self.name}>"


# 工作流节点模型
class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    node_type = Column(String, nullable=False)  # 开始、审批、结束等
    approver_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    order_index = Column(Integer, nullable=False)  # 节点顺序
    is_final = Column(Boolean, default=False)  # 是否为最终节点
    reject_to_node_id = Column(Integer, ForeignKey("workflow_nodes.id"), nullable=True)
    multi_approve_type = Column(String, default="any")  # 'any' - 任一审批, 'all' - 所有人审批
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    workflow = relationship("Workflow", back_populates="nodes")
    approver_role = relationship("Role", foreign_keys=[approver_role_id])
    reject_to_node = relationship("WorkflowNode", remote_side=[id])
    approvers = relationship("User", secondary=workflow_node_approvers, backref="workflow_nodes")
    instance_nodes = relationship("WorkflowInstanceNode", back_populates="workflow_node")

    def __repr__(self):
        return f"<WorkflowNode {self.name}>"


# 工作流实例模型
class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    # Phase 2 (重构方案): 实例与业务对象的绑定泛化为 subject_type + subject_id。
    # 此前 ledger_id NOT NULL + UNIQUE 把引擎焊死在台账上, 画像只好自建两套
    # 审批状态机。现在: 台账实例 subject_type='ledger' (ledger_id 仍同步写,
    # 台账读写路径零改动), 画像实例 subject_type='portrait_submission' /
    # 'portrait_home_visit' (ledger_id 为 NULL —— SQLite UNIQUE 允许多个 NULL,
    # 存量库的旧唯一索引无需重建)。
    __table_args__ = (
        UniqueConstraint("subject_type", "subject_id", name="uq_workflow_instance_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    #TODO 去掉外键约束
    # ledger_id = Column(Integer, ForeignKey("ledgers.id"), nullable=False, unique=True)  # 确保一对一关系
    ledger_id = Column(Integer, nullable=True, index=True)  # 台账路径兼容列; 画像实例为 NULL
    subject_type = Column(String(50), nullable=False, default="ledger", index=True)
    subject_id = Column(Integer, nullable=True)
    status = Column(String, default="active")  # active, completed, cancelled, rejected
    current_node_id = Column(Integer, nullable=True)  # 移除外键约束，避免循环引用
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    workflow = relationship("Workflow", back_populates="instances")
    # ledger = relationship("Ledger", back_populates="workflow_instance", uselist=False)  # 确保一对一关系
    creator = relationship("User", foreign_keys=[created_by])
    instance_nodes = relationship("WorkflowInstanceNode", back_populates="workflow_instance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowInstance {self.id}>"


# 工作流实例节点模型
class WorkflowInstanceNode(Base):
    __tablename__ = "workflow_instance_nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=False)
    workflow_node_id = Column(Integer, ForeignKey("workflow_nodes.id"), nullable=False)
    status = Column(String, default=ApprovalStatus.PENDING)  # pending, approved, rejected
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    approver_actions = Column(JSON, default=list)  # 存储审批人的操作记录 [{user_id, action, comment, timestamp}]

    # 关系
    workflow_instance = relationship("WorkflowInstance", back_populates="instance_nodes", foreign_keys=[workflow_instance_id])
    workflow_node = relationship("WorkflowNode", back_populates="instance_nodes")
    approver = relationship("User", foreign_keys=[approver_id])

    def __repr__(self):
        return f"<WorkflowInstanceNode {self.id}>" 