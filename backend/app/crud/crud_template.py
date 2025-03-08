from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate

class CRUDTemplate(CRUDBase[Template, TemplateCreate, TemplateUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Template]:
        return db.query(Template).filter(Template.name == name).first()
    
    def get_by_department(self, db: Session, *, department: str, skip: int = 0, limit: int = 100) -> List[Template]:
        return db.query(Template).filter(Template.department == department).offset(skip).limit(limit).all()

template = CRUDTemplate(Template)
