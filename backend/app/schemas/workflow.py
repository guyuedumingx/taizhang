from typing import List, Optional, Any, Dict, ForwardRef, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime

# 处理循环引用
if TYPE_CHECKING:
    from app.schemas.user import User
else:
    User = ForwardRef('User')

# 工作流节点基础模型
class WorkflowNodeBase(BaseModel):
    name: str
    description: Optional[str] = None
    node_type: str
    approver_role_id: Optional[int] = None
    approver_user_id: Optional[int] = None
    order_index: int
    is_final: Optional[bool] = None
    reject_to_node_id: Optional[int] = None
    multi_approve_type: Optional[str] = "any"  # 'any' - 任一审批, 'all' - 所有人审批
    need_select_next_approver: Optional[bool] = False

# 创建工作流节点请求
class WorkflowNodeCreate(WorkflowNodeBase):
    workflow_id: int
    approver_ids: Optional[List[int]] = []  # 多个审批人ID

# 用于CRUD的WorkflowNodeCreate，包含ID
class WorkflowNodeCreateWithId(WorkflowNodeCreate):
    id: Optional[int] = None

# 数据库中的工作流节点
class WorkflowNodeInDBBase(WorkflowNodeBase):
    id: int
    workflow_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

# 返回给API的工作流节点
class WorkflowNode(WorkflowNodeInDBBase):
    approver_role_name: Optional[str] = None
    approver_user_name: Optional[str] = None
    approvers: Optional[List[Any]] = []  # 使用Any类型避免循环引用问题
    
    class Config:
        orm_mode = True
        from_attributes = True
        arbitrary_types_allowed = True  # 允许任意类型序列化

# 更新工作流节点请求
class WorkflowNodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    node_type: Optional[str] = None
    approver_role_id: Optional[int] = None
    approver_user_id: Optional[int] = None
    order_index: Optional[int] = None
    is_final: Optional[bool] = None
    reject_to_node_id: Optional[int] = None
    multi_approve_type: Optional[str] = None
    need_select_next_approver: Optional[bool] = None
    approver_ids: Optional[List[int]] = None  # 多个审批人ID

# 工作流基础模型
class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True

# 创建工作流请求
class WorkflowCreate(WorkflowBase):
    nodes: Optional[List[WorkflowNodeCreate]] = []

# 数据库中的工作流
class WorkflowInDBBase(WorkflowBase):
    id: int
    created_by: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

# 返回给API的工作流
class Workflow(WorkflowInDBBase):
    template_name: Optional[str] = None
    nodes: Optional[List[WorkflowNode]] = []
    creator_name: Optional[str] = None
    node_count: Optional[int] = 0
    
    class Config:
        orm_mode = True
        from_attributes = True
        arbitrary_types_allowed = True  # 允许任意类型序列化

# 更新工作流请求
class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    nodes: Optional[List[WorkflowNodeCreate]] = None

# 审批人操作记录
class ApproverAction(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    action: str  # 'approve', 'reject', 'comment'
    comment: Optional[str] = None
    timestamp: Optional[datetime] = None

# 为兼容性导出为ApprovalAction
ApprovalAction = ApproverAction

# 工作流实例节点基础模型
class WorkflowInstanceNodeBase(BaseModel):
    workflow_instance_id: int
    workflow_node_id: int
    status: str = 'pending'
    approver_id: Optional[int] = None
    comment: Optional[str] = None

# 创建工作流实例节点请求
class WorkflowInstanceNodeCreate(WorkflowInstanceNodeBase):
    pass

# 数据库中的工作流实例节点
class WorkflowInstanceNodeInDBBase(WorkflowInstanceNodeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approver_actions: Optional[List[Dict[str, Any]]] = []

    class Config:
        orm_mode = True
        from_attributes = True

# 返回给API的工作流实例节点
class WorkflowInstanceNode(WorkflowInstanceNodeInDBBase):
    approver_name: Optional[str] = None
    node_name: Optional[str] = None
    node_type: Optional[str] = None

# 更新工作流实例节点请求
class WorkflowInstanceNodeUpdate(BaseModel):
    status: Optional[str] = None
    approver_id: Optional[int] = None
    comment: Optional[str] = None
    completed_at: Optional[datetime] = None
    add_action: Optional[ApproverAction] = None

# 工作流实例基础模型
class WorkflowInstanceBase(BaseModel):
    workflow_id: int
    ledger_id: int
    status: str = 'active'
    current_node_id: Optional[int] = None

# 创建工作流实例请求
class WorkflowInstanceCreate(WorkflowInstanceBase):
    created_by: int

# 数据库中的工作流实例
class WorkflowInstanceInDBBase(WorkflowInstanceBase):
    id: int
    created_by: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

# 返回给API的工作流实例
class WorkflowInstance(WorkflowInstanceInDBBase):
    workflow_name: Optional[str] = None
    ledger_name: Optional[str] = None
    creator_name: Optional[str] = None
    current_node_name: Optional[str] = None
    nodes: Optional[List[WorkflowInstanceNode]] = []
    current_node: Optional[WorkflowInstanceNode] = None

# 更新工作流实例请求
class WorkflowInstanceUpdate(BaseModel):
    status: Optional[str] = None
    current_node_id: Optional[int] = None
    completed_at: Optional[datetime] = None

# 提交台账工作流请求
class LedgerSubmitWorkflow(BaseModel):
    workflow_id: int
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None

# 处理审批请求
class ProcessApproval(BaseModel):
    action: str  # 'approve', 'reject'
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None

# 工作流节点审批请求
class WorkflowNodeApproval(BaseModel):
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None

# 工作流节点拒绝请求
class WorkflowNodeRejection(BaseModel):
    comment: Optional[str] = None

# 解决循环引用
from app.schemas.user import User
Workflow.model_rebuild()
WorkflowNode.model_rebuild() 