from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel
from app.schemas.workflow import WorkflowInstance


# 共享属性
class LedgerBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    team_id: Optional[int] = None
    template_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = "draft"


# 创建台账时的属性
class LedgerCreate(LedgerBase):
    # 名称可选，可以从模板获取默认值
    template_id: int  # 必须指定模板ID


# 更新台账时的属性
class LedgerUpdate(LedgerBase):
    pass


# 提交台账审核
class LedgerSubmit(BaseModel):
    # workflow_id: Optional[int] = None  # 如果不提供，将使用模板默认工作流
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None  # 仅在需要指定下一审批人时使用


# 台账审批
class LedgerApproval(BaseModel):
    action: str  # "approve" 或 "reject"
    comment: Optional[str] = None
    next_approver_id: Optional[int] = None  # 仅在需要指定下一审批人时使用


# 数据库中的台账
class LedgerInDBBase(LedgerBase):
    id: int
    created_by_id: int
    updated_by_id: int
    current_approver_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 返回给API的台账
class Ledger(LedgerInDBBase):
    team_name: Optional[str] = None
    template_name: Optional[str] = None
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    current_approver_name: Optional[str] = None
    workflow_name: Optional[str] = None
    active_workflow_instance: Optional[WorkflowInstance] = None  # 当前活动的工作流实例 