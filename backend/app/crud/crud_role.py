from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.casbin_service import add_permission_for_role, get_enforcer_instance

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name == name).first()
        
    def create(self, db: Session, *, obj_in: RoleCreate) -> Role:
        """创建角色并设置权限"""
        # 从输入数据中提取角色属性（排除permissions）
        role_data = obj_in.dict(exclude={"permissions"})
        
        # 创建角色实例
        db_obj = Role(**role_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # 添加权限
        permissions = obj_in.permissions or []
        for permission in permissions:
            # 解析权限字符串，格式: "resource:action"
            if ":" in permission:
                resource, action = permission.split(":", 1)
                add_permission_for_role(db_obj.name, resource, action)
        
        return db_obj

role = CRUDRole(Role)
