from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel


# 共享属性
class LedgerBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "draft"
    team_id: Optional[int] = None
    template_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


# 创建台账时的属性
class LedgerCreate(LedgerBase):
    name: str
    team_id: Optional[int] = None
    template_id: Optional[int] = None


# 更新台账时的属性
class LedgerUpdate(LedgerBase):
    pass


# 数据库中的台账
class LedgerInDBBase(LedgerBase):
    id: int
    created_by_id: int
    updated_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 返回给API的台账
class Ledger(LedgerInDBBase):
    team_name: Optional[str] = None
    template_name: Optional[str] = None
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None 