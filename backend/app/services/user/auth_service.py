from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import create_access_token, verify_password, get_password_hash
from app.services.casbin_service import get_roles_for_user, get_permissions_for_role, add_role_for_user


class AuthService:
    """认证服务类，处理用户认证相关的业务逻辑"""

    @staticmethod
    def authenticate_user(db: Session, ehr_id: str, password: str) -> Dict[str, Any]:
        """用户认证"""
        # 使用EHR号查找用户
        user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="EHR号或密码错误")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="EHR号或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="用户已被禁用")
        
        # 获取用户角色
        roles = get_roles_for_user(str(user.id))
        
        # 检查密码是否过期
        password_expired = False
        if user.last_password_change:
            three_months_ago = datetime.now() - timedelta(days=90)
            password_expired = user.last_password_change < three_months_ago
        
        # 获取用户权限
        permissions = []
        for role in roles:
            role_permissions = get_permissions_for_role(role)
            for p in role_permissions:
                # p格式为 [role, resource, action]
                if len(p) >= 3:
                    permission = f"{p[1]}:{p[2]}"
                    if permission not in permissions:
                        permissions.append(permission)
        
        # 如果是超级管理员，添加所有权限
        if user.is_superuser:
            permissions = ["*:*"]
        
        access_token = create_access_token(
            data={"sub": str(user.id), "roles": roles}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "roles": roles,
            "password_expired": password_expired,
            "permissions": permissions,
            "team_id": user.team_id
        }

    @staticmethod
    def register_user(db: Session, user_in: schemas.UserCreate) -> models.User:
        """注册新用户"""
        # 检查用户名是否已存在
        user = db.query(models.User).filter(models.User.username == user_in.username).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="用户名已存在",
            )
        
        # 检查EHR号是否已存在
        user = db.query(models.User).filter(models.User.ehr_id == user_in.ehr_id).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="EHR号已存在",
            )
        
        # 创建新用户
        user = models.User(
            username=user_in.username,
            ehr_id=user_in.ehr_id,
            hashed_password=get_password_hash(user_in.password),
            name=user_in.name,
            department=user_in.department if user_in.department else "未分配",
            is_active=True,
            is_superuser=False,
            team_id=user_in.team_id,
            last_password_change=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 为新用户分配默认角色
        add_role_for_user(str(user.id), "user")
        
        return user

    @staticmethod
    def change_password(db: Session, user_id: int, password_data: schemas.PasswordChange) -> Dict[str, str]:
        """修改密码"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证旧密码
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码不正确")
        
        # 检查新密码是否与当前密码相同
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
        
        # 设置新密码
        user.hashed_password = get_password_hash(password_data.new_password)
        user.last_password_change = datetime.now()
        db.commit()
        
        return {"message": "密码修改成功"}


auth_service = AuthService() 