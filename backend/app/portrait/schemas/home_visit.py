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
    # PRD 附录 B.4 第 14 列「家访记录表扫描件」: 已提交 / 未提交。
    # 与 scan_file_path 是两件事 —— 后者说明传了文件, 前者说明业务上这张记录表交没交。
    scan_status: Optional[str] = Field(
        None, pattern="^(已提交|未提交)$", description="扫描件提交状态 (B.4 第 14 列)"
    )


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
    scan_status: Optional[str] = Field(None, pattern="^(已提交|未提交)$")


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


# ============================================================================
# F11 批量导入 (PRD 附录 B.4 的 14 列)
# ============================================================================
class HomeVisitImportRow(BaseModel):
    """批量导入 Excel 一行。

    对应 B.4 的 14 列, 其中 3 列不在本模型里:
      - 第 10 列「家访人员及岗位」: 导入场景下**故意不解析**。该列是签字内容,
        Excel 里的文本无法保证与 users.department 一致, 照抄会让 visitor_info
        里的家访人和实际签字人对不上 (业务规则"谁做家访谁签字")。后端一律用
        home_visit_service._build_visitor_info() 按导入人重建。
      - 第 13 列「序号」: 展示用, 无业务含义。
      - 第 1 列「所属团队」: 由后端强制写死 "审核处理团队", 导入时校验 Excel 值
        是否等于它, 不等则该行失败。
    """
    row_number: int
    visited_ehr_id: str
    visited_full_name: str
    visited_job_title: Optional[str] = None
    visited_phone: Optional[str] = None
    visit_year: int
    visit_time: datetime
    visit_method: str = Field(..., pattern="^(线上|线下)$")
    visit_address: Optional[str] = None
    is_visited: bool = False
    remarks: Optional[str] = None
    scan_status: Optional[str] = Field(None, pattern="^(已提交|未提交)$")


class HomeVisitImportSummary(BaseModel):
    """批量导入结果 (Rule 12: 失败必须显性化)"""
    success_count: int
    failed_count: int
    failed_rows: list[dict]


# ============================================================================
# F12 家访年度矩阵 (PRD 附录 B.2)
# ============================================================================
class HomeVisitMatrixCell(BaseModel):
    """单元格: 填该年**具体家访日期** (B.2 第 4-7 列), 空白表示未家访。

    B.2 与 §7.2 在这里有冲突 —— §7.2 写"仅绿色", B.2 写"填具体日期"。
    两者不冲突: 日期是数据, 绿色是它的呈现, 由前端决定着色。这里只给数据。
    """
    visit_date: Optional[str] = None      # "2026-05-12"
    count: int = 0                        # 该年家访次数
    value: str = ""                       # 展示文本: 首次日期 + "+N" (该年被访多次)


class HomeVisitMatrixRow(BaseModel):
    """矩阵行 = 一名员工 (B.2: 序号 / 姓名 / EHR / 各年日期 / 家访年度汇总 / 分组)"""
    seq: int
    user_id: int
    ehr_id: str
    name: str
    team_name: str
    cells: list[HomeVisitMatrixCell] = []
    # 家访年度汇总 (B.2 第 8 列): "2023年/2026年", 从未家访为空
    visited_years: str = ""


class HomeVisitMatrix(BaseModel):
    """F12 矩阵响应: 列 = 年份, 行 = 员工"""
    columns: list[dict]          # [{"year": 2023}, ...]
    rows: list[HomeVisitMatrixRow]
    total_years: int
    total_visited_users: int     # 被家访过至少一次的人数