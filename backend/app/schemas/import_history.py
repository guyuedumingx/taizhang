"""导入历史相关 Schemas"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ImportHistoryItem(BaseModel):
    """导入历史列表条目(按批次聚合)"""
    batch_id: str
    template_id: int
    template_name: str
    imported_by_id: int
    imported_by_name: Optional[str] = None
    imported_at: datetime
    total_rows: int
    success_count: int
    failed_count: int
    filename: Optional[str] = None


class ImportHistoryDetail(ImportHistoryItem):
    """单批次详情(含台账 ID 列表)"""
    created_ledger_ids: List[int] = []
    failed_items: Optional[list] = None  # ImportFailedItem 列表,序列化后挂在这里


class ImportHistoryList(BaseModel):
    total: int
    items: List[ImportHistoryItem]
