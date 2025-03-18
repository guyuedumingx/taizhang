from typing import List, Union, Dict, Any

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.field_value import FieldValue
from app.schemas.field_value import FieldValueCreate, FieldValueUpdate


class CRUDFieldValue(CRUDBase[FieldValue, FieldValueCreate, FieldValueUpdate]):
    """FieldValue的CRUD操作"""

    def get_by_ledger_and_field(self, db: Session, *, ledger_id: int, field_id: int) -> FieldValue:
        """根据台账ID和字段ID获取台账项"""
        return db.query(self.model).filter(
            self.model.ledger_id == ledger_id,
            self.model.field_id == field_id
        ).first()

    def get_by_ledger(self, db: Session, *, ledger_id: int, skip: int = 0, limit: int = 100) -> List[FieldValue]:
        """获取台账的所有字段值"""
        return db.query(self.model).filter(
            self.model.ledger_id == ledger_id
        ).offset(skip).limit(limit).all()

    def get_by_field(self, db: Session, *, field_id: int, skip: int = 0, limit: int = 100) -> List[FieldValue]:
        """获取使用特定字段的所有台账项中的值"""
        return db.query(self.model).filter(
            self.model.field_id == field_id
        ).offset(skip).limit(limit).all()


# 创建CRUD实例，可以通过 crud.field_value 访问
field_value = CRUDFieldValue(FieldValue)
ledger_item = CRUDFieldValue(FieldValue)  # 兼容测试用例 