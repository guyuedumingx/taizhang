"""
portrait Submission + Approval schema

3 类提交 (PRD §9.1):
  - special_work  : 专项工作 (审批人下拉指定)
  - profile_edit  : 档案字段修改 (admin 审批)
  - skill_tag_edit: 亮点标签修改 (admin 审批, 高敏感必走)

注: 家访走独立表 portrait_home_visit_records, 审批流绑 workflow_instance_id,
    不在 submission 表范围 (PRD §9.1 §C)

集成指南 §5 雷区 6: portrait status 用 String 不用 taizhang ApprovalStatus 枚举
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# SubmissionRecord
# ============================================================================
class SubmissionBase(BaseModel):
    submission_type: str = Field(..., pattern="^(special_work|profile_edit|skill_tag_edit)$")
    payload: Any = Field(..., description="业务数据 (dict 或 JSON 字符串, 按 submission_type 分发字段)")


class SubmissionCreate(SubmissionBase):
    """创建并提交 (一步到 pending)"""
    next_approver_id: Optional[int] = Field(
        None, description="指定下一审批人 (special_work 必填, 其他类型选填, 默认 admin)"
    )


class SubmissionUpdate(BaseModel):
    """草稿更新 (仅 draft 状态可用, MVP 暂不实现)"""
    payload: Optional[Dict[str, Any]] = None


class SubmissionInDBBase(SubmissionBase):
    id: int
    submitter_user_id: int
    submitter_name: str
    submitter_ehr_id: str
    workflow_instance_id: Optional[int] = None
    current_approver_id: Optional[int] = None
    status: str
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Submission(SubmissionInDBBase):
    """返回给 API 的 Submission"""
    current_approver_name: Optional[str] = None
    approval_count: int = 0  # 关联审批操作数


class SubmissionDetail(Submission):
    """B4 提交详情页: 完整表单 + 审批流"""
    approvals: List["ApprovalRecord"] = Field(default_factory=list)


# ============================================================================
# ApprovalRecord
# ============================================================================
class ApprovalRecordBase(BaseModel):
    action: str = Field(..., pattern="^(submit|approve|reject|transfer|withdraw)$")
    comment: Optional[str] = None
    transferred_to_id: Optional[int] = None


class ApprovalRecordCreate(ApprovalRecordBase):
    submission_id: int


class ApprovalRecord(ApprovalRecordBase):
    id: int
    submission_id: int
    approver_id: int
    approver_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 审批动作 (E2 审批详情+操作)
# ============================================================================
class ApprovalActionRequest(BaseModel):
    """通过 / 驳回 / 转交 共用 body"""
    comment: Optional[str] = None
    transferred_to_id: Optional[int] = Field(
        None, description="转交时必填 (action=transfer)"
    )


class ApprovalActionResponse(BaseModel):
    """审批动作结果"""
    success: bool
    message: str
    submission: Optional[Submission] = None


# ============================================================================
# 我的提交列表查询参数
# ============================================================================
class MySubmissionsQuery(BaseModel):
    """我的提交列表 (B3)"""
    status: Optional[str] = Field(
        None, pattern="^(draft|pending|approved|rejected|cancelled)$"
    )
    submission_type: Optional[str] = Field(
        None, pattern="^(special_work|profile_edit|skill_tag_edit)$"
    )
    skip: int = 0
    limit: int = 50