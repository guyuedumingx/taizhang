from typing import Optional
from pydantic import BaseModel


class FieldValueBase(BaseModel):
    """用于FieldValue的基本属性"""
    ledger_id: Optional[int] = None
    field_id: Optional[int] = None
    value: Optional[str] = None


class FieldValueCreate(FieldValueBase):
    """创建FieldValue时的参数"""
    field_id: int
    # ledger_id可以通过参数传递，所以这里改为Optional
    ledger_id: Optional[int] = None


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


# 以下类用于向后兼容，实际使用时请直接使用FieldValue相关类
# 这些类将在未来版本中移除
class LedgerItemCreate(FieldValueCreate):
    """兼容原来的测试用例，请使用FieldValueCreate"""
    pass


class LedgerItemUpdate(FieldValueUpdate):
    """兼容原来的测试用例，请使用FieldValueUpdate"""
    pass 