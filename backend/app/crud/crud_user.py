from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.casbin_service import check_permission, get_roles_for_user, get_permissions_for_role

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """创建新用户，正确处理密码加密"""
        db_obj = User(
            username=obj_in.username,
            ehr_id=obj_in.ehr_id,
            hashed_password=get_password_hash(obj_in.password),
            name=obj_in.name,
            department=obj_in.department,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            team_id=obj_in.team_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
        
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

    def has_permission(self, db: Session, user_id: int, permission: str) -> bool:
        """检查用户是否拥有指定权限"""
        user = self.get(db, id=user_id)
        if not user:
            return False
        
        # 超级用户拥有所有权限
        if user.is_superuser:
            return True
        
        # 使用Casbin检查直接权限
        if check_permission(str(user.id), permission.split(":")[0], permission.split(":")[1]):
            return True
        
        # 获取用户角色
        roles = get_roles_for_user(str(user.id))
        
        # 超级管理员角色拥有所有权限
        if "admin" in roles:
            return True
        
        # 检查每个角色的权限
        for role in roles:
            role_permissions = get_permissions_for_role(role)
            
            for p in role_permissions:
                if len(p) >= 3:
                    # 通配符匹配: *, *
                    if p[1] == "*" and p[2] == "*":
                        return True
                    
                    # 资源通配符匹配: ledger, *
                    if p[1] == permission.split(":")[0] and p[2] == "*":
                        return True
                    
                    # 精确匹配: ledger, view
                    if p[1] == permission.split(":")[0] and p[2] == permission.split(":")[1]:
                        return True
        
        return False

user = CRUDUser(User)
