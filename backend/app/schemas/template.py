from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel

from app.schemas.field import Field, FieldCreate, FieldUpdate


# 共享属性
class TemplateBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    is_system: Optional[bool] = False
    workflow_id: Optional[int] = None
    
    # 台账元字段（默认值）
    default_description: Optional[str] = None
    default_metadata: Optional[Dict[str, Any]] = None


# 创建模板时的属性
class TemplateCreate(TemplateBase):
    name: str
    department: str
    fields: List[FieldCreate] = []


# 更新模板时的属性
class TemplateUpdate(TemplateBase):
    fields: Optional[List[FieldUpdate]] = None


# 数据库中的模板
class TemplateInDBBase(TemplateBase):
    id: int
    created_by_id: int
    updated_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 返回给API的模板
class Template(TemplateInDBBase):
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    fields_count: Optional[int] = None
    ledgers_count: Optional[int] = None


# 返回给API的模板详情
class TemplateDetail(Template):
    fields: List[Field] = [] 