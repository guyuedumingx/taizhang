"""
portrait G7 组员调换历史 schema (PRD §11.4)

**故意不提供 Create/Update** — 记录由 team_id 变更自动写入 (用户 2026-10-12 决定),
手工新增会造假。删除仅用于 admin 纠错。
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GroupTransferBase(BaseModel):
    """持久化字段 (与 GroupTransferHistory 模型一一对应)"""
    ehr_no: str = Field(..., max_length=50, description="员工 EHR 号")
    from_group: Optional[str] = Field(
        None, max_length=100, description="原组名 (无 = 此前未分组)"
    )
    to_group: str = Field(
        ..., max_length=100, description="新组名 (退组时为占位值「未分组」)"
    )
    # 授权用这两个整数, 组名仅供展示 (teams 表允许重名, 按名字过滤会越权)
    from_team_id: Optional[int] = Field(
        None, description="原组 id (NULL = 此前未分组)"
    )
    to_team_id: Optional[int] = Field(
        None, description="新组 id (NULL = 退组后未分组)"
    )
    transfer_date: datetime = Field(..., description="调组时间")
    leave_date: Optional[datetime] = Field(
        None, description="离组时间; NULL = 该员工目前仍在此组"
    )
    operator_ehr_no: str = Field(..., max_length=50, description="操作人 EHR 号")
    operator_name: str = Field(..., max_length=100, description="操作人姓名")
    reason: Optional[str] = Field(None, max_length=500, description="调组原因")
    remark: Optional[str] = Field(None, max_length=500, description="备注")
    created_at: datetime = Field(..., description="记录创建时间")


class GroupTransferRecord(GroupTransferBase):
    """列表项 — 在持久化字段外多两个派生字段"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: Optional[str] = Field(
        None, description="员工姓名 (联表带出; 用户被删除后为 None)"
    )
    is_current: bool = Field(..., description="是否当前在组 (= leave_date is None)")


class GroupTransferListResponse(BaseModel):
    """分页响应 (与 entry_exit / home_visit 一致)"""
    items: List[GroupTransferRecord]
    total: int
    page: int
    size: int
