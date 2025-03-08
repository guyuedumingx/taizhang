from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    def get_multi_by_team(self, db: Session, *, team_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).filter(User.team_id == team_id).offset(skip).limit(limit).all()

user = CRUDUser(User)
