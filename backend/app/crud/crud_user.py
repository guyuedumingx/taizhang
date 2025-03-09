from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_ehr_id(self, db: Session, *, ehr_id: str) -> Optional[User]:
        return db.query(User).filter(User.ehr_id == ehr_id).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    def get_multi_by_team(self, db: Session, *, team_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).filter(User.team_id == team_id).offset(skip).limit(limit).all()
    
    def is_superuser(self, user: User) -> bool:
        """
        检查用户是否为超级管理员
        """
        return user.is_superuser if hasattr(user, "is_superuser") else False
    
    def is_active(self, user: User) -> bool:
        """
        检查用户是否处于活动状态
        """
        return user.is_active if hasattr(user, "is_active") else False
    
    def has_role_permission(self, user: User, resource: str, action: str) -> bool:
        """
        检查用户是否有特定资源的特定操作权限
        """
        # 如果用户是超级管理员，直接返回 True
        if self.is_superuser(user):
            return True
        
        # 检查用户角色权限
        if hasattr(user, "role") and user.role:
            if hasattr(user.role, "permissions"):
                for perm in user.role.permissions:
                    if perm.resource == resource and perm.action == action:
                        return True
        return False

user = CRUDUser(User)
