from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

# 工作流节点基础模型
class WorkflowNodeBase(BaseModel):
    name: str
    description: Optional[str] = None
    node_type: str  # 开始、审批、结束等
    approver_role_id: Optional[int] = None
    approver_user_id: Optional[int] = None
    order_index: int
    is_final: bool = False
    reject_to_node_id: Optional[int] = None

# 创建工作流节点模型
class WorkflowNodeCreate(WorkflowNodeBase):
    workflow_id: int

# 更新工作流节点模型
class WorkflowNodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    approver_role_id: Optional[int] = None
    approver_user_id: Optional[int] = None
    order_index: Optional[int] = None
    is_final: Optional[bool] = None
    reject_to_node_id: Optional[int] = None

# 工作流节点响应模型
class WorkflowNode(WorkflowNodeBase):
    id: int
    workflow_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# 工作流基础模型
class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: int
    is_active: bool = True

# 创建工作流模型
class WorkflowCreate(WorkflowBase):
    nodes: List[WorkflowNodeCreate]

# 更新工作流模型
class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# 工作流响应模型
class Workflow(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    nodes: List[WorkflowNode] = []
    
    class Config:
        orm_mode = True

# 工作流实例节点基础模型
class WorkflowInstanceNodeBase(BaseModel):
    workflow_instance_id: int
    workflow_node_id: int
    status: str = "pending"
    approver_id: Optional[int] = None
    comment: Optional[str] = None

# 创建工作流实例节点模型
class WorkflowInstanceNodeCreate(WorkflowInstanceNodeBase):
    pass

# 更新工作流实例节点模型
class WorkflowInstanceNodeUpdate(BaseModel):
    status: Optional[str] = None
    approver_id: Optional[int] = None
    comment: Optional[str] = None
    completed_at: Optional[datetime] = None

# 工作流实例节点响应模型
class WorkflowInstanceNode(WorkflowInstanceNodeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# 工作流实例基础模型
class WorkflowInstanceBase(BaseModel):
    workflow_id: int
    ledger_id: int
    status: str = "active"

# 创建工作流实例模型
class WorkflowInstanceCreate(WorkflowInstanceBase):
    created_by: int

# 更新工作流实例模型
class WorkflowInstanceUpdate(BaseModel):
    status: Optional[str] = None
    current_node_id: Optional[int] = None
    completed_at: Optional[datetime] = None

# 工作流实例响应模型
class WorkflowInstance(WorkflowInstanceBase):
    id: int
    created_by: int
    current_node_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    nodes: List[WorkflowInstanceNode] = []
    
    class Config:
        orm_mode = True

# 审批操作模型
class ApprovalAction(BaseModel):
    action: str  # "approve" 或 "reject"
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None  # 仅在需要指定下一审批人时使用 