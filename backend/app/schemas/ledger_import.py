"""台账导入相关 Pydantic Schemas"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------- 导入配置 ----------

class ImportConfig(BaseModel):
    """单条模板导入配置(来自 ledger_import_config.json)"""
    template_name: str
    max_rows: int = 2000
    warn_rows: int = 5000
    max_rows_hard_limit: int = 5000
    name_field: Optional[str] = None
    unique_keys: List[str] = ["name"]
    identity_mapping: Dict[str, str] = {}
    field_order: List[str] = []


class ImportConfigList(BaseModel):
    configs: List[ImportConfig]


# ---------- 校验报告 ----------

class ImportIssue(BaseModel):
    row: int                     # Excel 行号(从 1 计,含表头偏移)
    type: str                    # missing_required / duplicate / team_not_found /
                                 # user_not_found / uncleanable_value / type_mismatch /
                                 # row_limit_exceeded
    field: Optional[str] = None  # 出问题的字段 label
    raw: Optional[Any] = None    # 原始值
    reason: str


class CleanablePreview(BaseModel):
    row: int
    field: str
    raw: Any
    clean: Any


class ImportValidationReport(BaseModel):
    template_id: int
    template_name: str
    preview_batch_id: str
    total_rows: int
    importable_count: int
    cleanable_count: int
    issues: List[ImportIssue] = []
    cleanable_previews: List[CleanablePreview] = []
    row_limit_warning: Optional[str] = None


# ---------- 提交结果 ----------

class ImportFailedItem(BaseModel):
    row: int
    field: Optional[str] = None
    raw: Optional[Any] = None
    reason: str


class ImportCommitResult(BaseModel):
    batch_id: str
    template_id: int
    template_name: str
    success_count: int
    failed_count: int
    elapsed_seconds: float
    created_ledger_ids: List[int] = []
    failed_items: List[ImportFailedItem] = []
    failures_download_url: Optional[str] = None
