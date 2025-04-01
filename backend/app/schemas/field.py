from typing import Optional, List, Any

from pydantic import BaseModel


# 共享属性
class FieldBase(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None
    default_value: Optional[str] = None
    order: int = 0
    is_key_field: bool = True  # 默认为关键字段


# 创建字段时的属性
class FieldCreate(FieldBase):
    name: str
    type: str


# 更新字段时的属性
class FieldUpdate(FieldBase):
    id: Optional[int] = None


# 数据库中的字段
class FieldInDBBase(FieldBase):
    id: int
    template_id: int

    class Config:
        orm_mode = True


# 返回给API的字段
class Field(FieldInDBBase):
    pass 