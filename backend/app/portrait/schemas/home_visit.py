"""
portrait HomeVisit schema (PRD §C §9.1)

家访走 4 类审批共用模式:
  draft → pending → approved / rejected / cancelled

集成指南 §5 雷区 6: status 用 String, 不复用台账 ApprovalStatus 枚举
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# HomeVisitRecord CRUD schemas
# ============================================================================
class HomeVisitBase(BaseModel):
    visit_year: int
    visit_time: datetime
    visit_method: str = Field(..., pattern="^(线上|线下)$")
    visit_address: Optional[str] = None
    visitor_info: Optional[str] = None
    is_visited: bool = False
    visit_date: Optional[date] = None
    position: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    mobile: Optional[str] = None
    home_phone: Optional[str] = None
    family1_name: Optional[str] = None
    family1_relation: Optional[str] = None
    family1_contact: Optional[str] = None
    family1_work_unit: Optional[str] = None
    family2_name: Optional[str] = None
    family2_relation: Optional[str] = None
    family2_contact: Optional[str] = None
    family2_work_unit: Optional[str] = None
    feedback: Optional[str] = None
    # C1 (PRD §7.1) 新增 — 双人员家访 + 扫描件 + 团队名称
    co_visitor_user_id: Optional[int] = Field(None, description="第二家访人 user_id (双人员家访)")
    scan_file_path: Optional[str] = Field(None, description="扫描件相对路径 uploads/portrait/home_visits/...")
    team_name: Optional[str] = Field(None, description='固定 "审核处理团队", 后端兜底默认填入')


class HomeVisitCreate(HomeVisitBase):
    """组长创建家访草稿"""
    visited_ehr_id: str = Field(..., description="被家访人 EHR 号")


class HomeVisitUpdate(BaseModel):
    """更新家访草稿 (仅 draft 状态)"""
    visit_year: Optional[int] = None
    visit_time: Optional[datetime] = None
    visit_method: Optional[str] = Field(None, pattern="^(线上|线下)$")
    visit_address: Optional[str] = None
    visitor_info: Optional[str] = None
    is_visited: Optional[bool] = None
    visit_date: Optional[date] = None
    position: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    mobile: Optional[str] = None
    home_phone: Optional[str] = None
    family1_name: Optional[str] = None
    family1_relation: Optional[str] = None
    family1_contact: Optional[str] = None
    family1_work_unit: Optional[str] = None
    family2_name: Optional[str] = None
    family2_relation: Optional[str] = None
    family2_contact: Optional[str] = None
    family2_work_unit: Optional[str] = None
    feedback: Optional[str] = None
    # C1 新增 — 草稿编辑可改
    co_visitor_user_id: Optional[int] = None
    scan_file_path: Optional[str] = None
    team_name: Optional[str] = None


# ============================================================================
# Status machine schemas (P6)
# ============================================================================
class HomeVisitSubmitRequest(BaseModel):
    """提交审批 (draft → pending)"""
    next_approver_id: Optional[int] = Field(
        None, description="指定审批人, 留空则默认 admin"
    )


class HomeVisitApproveRequest(BaseModel):
    """审批通过 (pending → approved)"""
    comment: Optional[str] = Field(None, description="审批备注 (选填)")


class HomeVisitRejectRequest(BaseModel):
    """审批驳回 (pending → rejected, 必须填备注)"""
    comment: str = Field(..., min_length=1, description="驳回理由 (必填, Rule 12 显性化)")


# ============================================================================
# Response
# ============================================================================
class HomeVisit(HomeVisitBase):
    """返回给 API 的家访详情 (含审批字段 P6)"""
    id: int
    visited_user_id: int
    visited_ehr_id: Optional[str] = None
    visited_name: Optional[str] = None
    visitor_user_id: int
    visitor_name: Optional[str] = None

    # P6 状态机字段
    status: str
    current_approver_id: Optional[int] = None
    current_approver_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # C1 新增 — 双人员家访第二人 (反查 name)
    co_visitor_user_id: Optional[int] = None
    co_visitor_name: Optional[str] = None
    scan_file_path: Optional[str] = None
    scan_file_url: Optional[str] = None  # 由 router 层拼装 /uploads/portrait/...
    team_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HomeVisitListItem(BaseModel):
    """家访列表项 (列表用, 字段精简)"""
    id: int
    visited_ehr_id: str
    visited_name: str
    visit_year: int
    visit_time: datetime
    visit_method: str
    is_visited: bool
    status: str
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    visitor_name: Optional[str] = None
    current_approver_name: Optional[str] = None
    # C1 新增 (列表也透出关键 3 字段)
    co_visitor_name: Optional[str] = None
    team_name: Optional[str] = None
    has_scan: bool = False  # 列表只显示是否有扫描件 (不暴露 path)
    created_at: datetime

    class Config:
        from_attributes = True


class HomeVisitListResponse(BaseModel):
    """列表响应 (含 total)"""
    total: int
    items: list[HomeVisitListItem]