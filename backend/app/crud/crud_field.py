from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.field import Field
from app.schemas.field import FieldCreate, FieldUpdate

class CRUDField(CRUDBase[Field, FieldCreate, FieldUpdate]):
    def get_by_template(self, db: Session, *, template_id: int, skip: int = 0, limit: int = 100) -> List[Field]:
        return db.query(Field).filter(Field.template_id == template_id).offset(skip).limit(limit).all()
    
    def get_by_name_and_template(self, db: Session, *, name: str, template_id: int) -> Optional[Field]:
        return db.query(Field).filter(Field.name == name, Field.template_id == template_id).first()

field = CRUDField(Field)
