from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.models.role import Role
from app.services.casbin_service import (
    add_permission_for_role,
    get_permissions_for_role,
    remove_permission_for_role,
    add_role_for_user,
    remove_role_for_user,
    get_roles_for_user,
    get_enforcer_instance
)

class RoleService:
    @staticmethod
    def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
        """
        获取所有角色列表
        """
        # 获取所有角色
        roles = crud.role.get_multi(db, skip=skip, limit=limit)
        
        # 获取每个角色的权限
        for role in roles:
            # 使用casbin获取权限
            permissions = get_permissions_for_role(role.name)
            # 转换权限格式
            role_permissions = []
            for p in permissions:
                if len(p) >= 2:
                    # Casbin 策略格式为: [role, obj, act]
                    obj, act = p[1], p[2]
                    if obj == "*" and act == "*":
                        role_permissions.append("*:*")  # 所有权限
                    elif act == "*":
                        role_permissions.append(f"{obj}:*")  # 所有操作权限
                    else:
                        role_permissions.append(f"{obj}:{act}")  # 具体权限
            
            role.permissions = role_permissions
        
        return roles

    @staticmethod
    def create_role(db: Session, role_in: schemas.RoleCreate) -> Role:
        """
        创建新角色
        """
        # 检查角色名是否已存在
        role = crud.role.get_by_name(db, name=role_in.name)
        if role:
            raise HTTPException(
                status_code=400,
                detail="同名角色已存在",
            )
        
        # 创建新角色
        role = crud.role.create(db, obj_in=role_in)
        
        # 添加权限
        if role_in.permissions:
            enforcer = get_enforcer_instance()
            for permission in role_in.permissions:
                # 解析权限格式
                if permission == "*:*":
                    # 所有权限
                    enforcer.add_policy(role.name, "*", "*")
                elif permission.endswith(":*"):
                    # 某个对象的所有操作权限
                    obj = permission.split(":")[0]
                    enforcer.add_policy(role.name, obj, "*")
                else:
                    # 具体权限
                    parts = permission.split(":")
                    if len(parts) == 2:
                        obj, act = parts
                        enforcer.add_policy(role.name, obj, act)
        
        # 获取角色权限
        permissions = get_permissions_for_role(role.name)
        role_permissions = []
        for p in permissions:
            if len(p) >= 2:
                obj, act = p[1], p[2]
                if obj == "*" and act == "*":
                    role_permissions.append("*:*")
                elif act == "*":
                    role_permissions.append(f"{obj}:*")
                else:
                    role_permissions.append(f"{obj}:{act}")
        
        role.permissions = role_permissions
        
        return role

    @staticmethod
    def get_role(db: Session, role_id: int) -> Role:
        """
        获取角色详情
        """
        # 检索角色
        role = crud.role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 获取角色权限
        permissions = get_permissions_for_role(role.name)
        role_permissions = []
        for p in permissions:
            if len(p) >= 2:
                obj, act = p[1], p[2]
                if obj == "*" and act == "*":
                    role_permissions.append("*:*")
                elif act == "*":
                    role_permissions.append(f"{obj}:*")
                else:
                    role_permissions.append(f"{obj}:{act}")
        
        role.permissions = role_permissions
        
        return role

    @staticmethod
    def update_role(db: Session, role_id: int, role_in: schemas.RoleUpdate) -> Role:
        """
        更新角色
        """
        # 获取角色
        role = crud.role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 检查是否是系统角色
        if role.is_system and (role_in.name or role_in.name != role.name):
            raise HTTPException(status_code=400, detail="不能修改系统角色名称")
        
        # 如果要修改角色名，检查是否存在同名角色
        if role_in.name and role_in.name != role.name:
            # 检查角色名是否已存在
            existing_role = crud.role.get_by_name(db, name=role_in.name)
            if existing_role:
                raise HTTPException(
                    status_code=400,
                    detail="同名角色已存在",
                )
        
        # 更新角色信息
        old_name = role.name
        role = crud.role.update(db, db_obj=role, obj_in=role_in)
        
        # 更新权限
        if role_in.permissions is not None:
            enforcer = get_enforcer_instance()
            
            # 如果角色名改变了，需要更新所有权限和角色分配
            if role_in.name and role_in.name != old_name:
                # 获取所有旧权限
                old_permissions = get_permissions_for_role(old_name)
                
                # 获取所有有该角色的用户
                users_with_role = enforcer.get_users_for_role(old_name)
                
                # 删除旧角色的所有权限
                enforcer.remove_filtered_policy(0, old_name)
                
                # 删除旧角色的所有角色分配
                for user in users_with_role:
                    enforcer.remove_grouping_policy(user, old_name)
                    enforcer.add_grouping_policy(user, role.name)
                
                # 添加新角色的权限
                for p in old_permissions:
                    if len(p) >= 2:
                        enforcer.add_policy(role.name, p[1], p[2])
            else:
                # 删除所有现有权限
                enforcer.remove_filtered_policy(0, role.name)
            
            # 添加新权限
            for permission in role_in.permissions:
                # 解析权限格式
                if permission == "*:*":
                    # 所有权限
                    enforcer.add_policy(role.name, "*", "*")
                elif permission.endswith(":*"):
                    # 某个对象的所有操作权限
                    obj = permission.split(":")[0]
                    enforcer.add_policy(role.name, obj, "*")
                else:
                    # 具体权限
                    parts = permission.split(":")
                    if len(parts) == 2:
                        obj, act = parts
                        enforcer.add_policy(role.name, obj, act)
        
        # 获取角色权限
        permissions = get_permissions_for_role(role.name)
        role_permissions = []
        for p in permissions:
            if len(p) >= 2:
                obj, act = p[1], p[2]
                if obj == "*" and act == "*":
                    role_permissions.append("*:*")
                elif act == "*":
                    role_permissions.append(f"{obj}:*")
                else:
                    role_permissions.append(f"{obj}:{act}")
        
        role.permissions = role_permissions
        
        return role

    @staticmethod
    def delete_role(db: Session, role_id: int) -> Role:
        """
        删除角色
        """
        role = crud.role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 检查是否是系统角色
        if role.is_system:
            raise HTTPException(status_code=400, detail="不能删除系统角色")
        
        # 删除角色的所有权限
        enforcer = get_enforcer_instance()
        enforcer.remove_filtered_policy(0, role.name)
        
        # 删除角色
        role = crud.role.remove(db, id=role_id)
        
        return role

    @staticmethod
    def get_user_roles(db: Session, user_id: int) -> List[str]:
        """
        获取用户的所有角色
        """
        # 检查用户是否存在
        user = crud.user.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取用户的所有角色
        roles = get_roles_for_user(str(user_id))
        
        return roles

    @staticmethod
    def add_user_role(db: Session, user_id: int, role_name: str) -> dict:
        """
        为用户添加角色
        """
        # 检查用户是否存在
        user = crud.user.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查角色是否存在
        role = crud.role.get_by_name(db, name=role_name)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 检查是否已经有这个角色
        user_roles = get_roles_for_user(str(user_id))
        if role_name in user_roles:
            return {"message": "用户已拥有该角色"}
        
        # 为用户添加角色
        result = add_role_for_user(str(user_id), role_name)
        if result:
            return {"message": "角色添加成功"}
        else:
            raise HTTPException(status_code=500, detail="角色添加失败")

    @staticmethod
    def remove_user_role(db: Session, user_id: int, role_name: str) -> dict:
        """
        删除用户的角色
        """
        # 检查用户是否存在
        user = crud.user.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查角色是否存在
        role = crud.role.get_by_name(db, name=role_name)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 检查用户是否有该角色
        user_roles = get_roles_for_user(str(user_id))
        if role_name not in user_roles:
            return {"message": "用户没有该角色"}
        
        # 删除用户的角色
        result = remove_role_for_user(str(user_id), role_name)
        if result:
            return {"message": "角色删除成功"}
        else:
            raise HTTPException(status_code=500, detail="角色删除失败")


role_service = RoleService() 