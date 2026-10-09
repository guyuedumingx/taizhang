"""
portrait 出入境台账 schema (PRD §10.1 F5-F9)
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EntryExitBase(BaseModel):
    """17 列字段 (PRD §10.1.2)"""
    name: str = Field(..., max_length=64, description="姓名")
    team_name: str = Field(..., max_length=128, description="团队")
    position: str = Field(..., max_length=64, description="职务")
    certificate_no: str = Field(..., max_length=64, description="证照号")
    outbound_reason: str = Field(..., description="出境原因")
    destination: str = Field(..., max_length=128, description="目的地")
    apply_depart_at: datetime = Field(..., description="申请离境")
    apply_return_at: datetime = Field(..., description="申请返回")
    certificate_type: str = Field(..., max_length=32, description="证照类别")
    apply_type: str = Field(..., max_length=32, description="申请类型")
    team_approver: str = Field(..., max_length=64, description="团队审批人")
    actual_depart_at: Optional[datetime] = Field(None, description="实际出境")
    actual_return_at: Optional[datetime] = Field(None, description="实际返回")
    year: int = Field(..., ge=2000, le=2100, description="年份")
    group_name: Optional[str] = Field(None, max_length=128, description="组别")
    remark: Optional[str] = Field(None, description="备注")

    @model_validator(mode="after")
    def check_dates(self):
        """校验: 申请离境 < 申请返回 (PRD §10.1.2 校验规则)"""
        if self.apply_depart_at and self.apply_return_at:
            if self.apply_depart_at >= self.apply_return_at:
                raise ValueError("申请离境必须早于申请返回")
        if self.actual_depart_at and self.actual_return_at:
            if self.actual_depart_at >= self.actual_return_at:
                raise ValueError("实际出境必须早于实际返回")
        return self


class EntryExitCreate(EntryExitBase):
    """新增 (F6). ehr_id 关联用户, 按 PRD EHR 校验规则"""
    ehr_id: str = Field(..., pattern=r"^\d{7}$", description="员工 EHR 号, 恰好 7 位数字")


class EntryExitUpdate(BaseModel):
    """编辑 (F8). 字段同新增, 全部可省略"""
    name: Optional[str] = Field(None, max_length=64)
    team_name: Optional[str] = Field(None, max_length=128)
    position: Optional[str] = Field(None, max_length=64)
    certificate_no: Optional[str] = Field(None, max_length=64)
    outbound_reason: Optional[str] = None
    destination: Optional[str] = Field(None, max_length=128)
    apply_depart_at: Optional[datetime] = None
    apply_return_at: Optional[datetime] = None
    certificate_type: Optional[str] = Field(None, max_length=32)
    apply_type: Optional[str] = Field(None, max_length=32)
    team_approver: Optional[str] = Field(None, max_length=64)
    actual_depart_at: Optional[datetime] = None
    actual_return_at: Optional[datetime] = None
    year: Optional[int] = Field(None, ge=2000, le=2100)
    group_name: Optional[str] = Field(None, max_length=128)
    remark: Optional[str] = None


class EntryExitRecord(EntryExitBase):
    """返回给 API 的出入境记录"""
    id: int
    ehr_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntryExitListResponse(BaseModel):
    """列表响应 (F5): 分页 + 顶部统计卡"""
    items: list[EntryExitRecord]
    total: int
    page: int
    size: int
    statistics: Optional["EntryExitStatistics"] = None


class EntryExitStatistics(BaseModel):
    """顶部统计卡 (F5): 累计记录 / 本年度 / 已关联证照 / 实际未返回"""
    total_count: int = 0
    current_year_count: int = 0
    distinct_certificate_count: int = 0
    not_returned_count: int = 0  # 实际返回为空


class EntryExitImportRow(BaseModel):
    """批量导入 Excel 行 (F9, 内部用)"""
    row_number: int
    ehr_id: str
    name: str
    team_name: str
    position: str
    certificate_no: str
    outbound_reason: str
    destination: str
    apply_depart_at: datetime
    apply_return_at: datetime
    certificate_type: str
    apply_type: str
    team_approver: str
    actual_depart_at: Optional[datetime] = None
    actual_return_at: Optional[datetime] = None
    year: int
    group_name: Optional[str] = None
    remark: Optional[str] = None


class EntryExitImportSummary(BaseModel):
    """批量导入结果 (F9, Rule 12: 失败显性化)"""
    success_count: int
    failed_count: int
    failed_rows: list[dict]  # [{row_number, ehr_id, reason}]
