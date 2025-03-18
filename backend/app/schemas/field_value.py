from typing import Optional
from pydantic import BaseModel


class FieldValueBase(BaseModel):
    """用于FieldValue的基本属性"""
    ledger_id: Optional[int] = None
    field_id: Optional[int] = None
    value: Optional[str] = None


class FieldValueCreate(FieldValueBase):
    """创建FieldValue时的参数"""
    ledger_id: int
    field_id: int


class FieldValueUpdate(FieldValueBase):
    """更新FieldValue时的参数"""
    pass


class FieldValueInDBBase(FieldValueBase):
    """数据库中的FieldValue包含的属性"""
    id: int
    ledger_id: int
    field_id: int

    class Config:
        from_attributes = True  # 允许从ORM模型创建


class FieldValue(FieldValueInDBBase):
    """返回给API的数据模型"""
    pass


class LedgerItemCreate(FieldValueCreate):
    """兼容原来的测试用例"""
    pass


class LedgerItemUpdate(FieldValueUpdate):
    """兼容原来的测试用例"""
    pass 