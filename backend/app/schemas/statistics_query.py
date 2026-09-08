"""多维度台账统计查询的请求/响应 schemas。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FieldFilterCondition(BaseModel):
    operator: str = "contains"  # contains/equals/gte/lte/between/in/normalized_between
    value: Any = None


class SystemFilters(BaseModel):
    status: List[str] = []
    approval_status: List[str] = []
    team_ids: List[int] = []
    created_by_ids: List[int] = []
    created_at_range: Optional[List[str]] = None   # ["2026-01-01", "2026-05-27"]
    updated_at_range: Optional[List[str]] = None


class StatisticsQueryRequest(BaseModel):
    template_ids: List[int] = []                   # 空 = 全部模板
    system_filters: SystemFilters = SystemFilters()
    field_filters: Dict[str, FieldFilterCondition] = {}
    keyword: str = ""
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


class LedgerQueryItem(BaseModel):
    id: int
    name: str
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    status: Optional[str] = None
    approval_status: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    data: Dict[str, Any] = {}


class SuspiciousItem(BaseModel):
    ledger_id: int
    ledger_name: str
    field: str
    raw: str
    reason: str


class FieldQuality(BaseModel):
    field_name: str
    sum: Optional[float] = None
    numeric_count: int = 0
    cleaned_count: int = 0        # 原始值脏但被规则修复的数量
    suspicious_count: int = 0
    suspicious_items: List[SuspiciousItem] = []


class DataQualityReport(BaseModel):
    total_count: int = 0
    fields: List[FieldQuality] = []


class LedgerQueryResponse(BaseModel):
    items: List[LedgerQueryItem]
    total: int
    page: int
    page_size: int
    data_quality: DataQualityReport


class QueryField(BaseModel):
    name: str
    label: str
    type: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None   # select 字段的选项
    has_pipeline: bool = False            # 是否配置了清洗规则链（数值型筛选）
