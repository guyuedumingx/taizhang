from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

# 系统日志基础模型
class SystemLogBase(BaseModel):
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    level: str
    module: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None

# 创建系统日志模型
class SystemLogCreate(SystemLogBase):
    pass

# 系统日志响应模型
class SystemLog(SystemLogBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# 审计日志基础模型
class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    ledger_id: Optional[int] = None
    workflow_instance_id: Optional[int] = None
    action: str
    status_before: Optional[str] = None
    status_after: Optional[str] = None
    comment: Optional[str] = None

# 创建审计日志模型
class AuditLogCreate(AuditLogBase):
    pass

# 审计日志响应模型
class AuditLog(AuditLogBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# 日志查询参数
class LogQueryParams(BaseModel):
    module: Optional[str] = None
    action: Optional[str] = None
    level: Optional[str] = None
    user_id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20 