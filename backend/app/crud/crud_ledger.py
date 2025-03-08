from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.crud.base import CRUDBase
from app.models.ledger import Ledger
from app.schemas.ledger import LedgerCreate, LedgerUpdate

class CRUDLedger(CRUDBase[Ledger, LedgerCreate, LedgerUpdate]):
    def get_by_template(self, db: Session, *, template_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(Ledger.template_id == template_id).offset(skip).limit(limit).all()
    
    def get_by_team(self, db: Session, *, team_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(Ledger.team_id == team_id).offset(skip).limit(limit).all()
    
    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(
            or_(
                Ledger.created_by_id == user_id,
                Ledger.current_approver_id == user_id
            )
        ).offset(skip).limit(limit).all()

ledger = CRUDLedger(Ledger)
