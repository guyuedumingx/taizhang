from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.services.casbin_service import get_roles_for_user, get_permissions_for_role, add_role_for_user

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    获取OAuth2访问令牌
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    
    # 获取用户角色
    roles = get_roles_for_user(str(user.id))
    
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
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 构建用户信息
    user_data = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": roles[0] if roles else "user",  # 使用第一个角色作为主角色
        "permissions": permissions,
        "teamId": user.team_id,
    }
    
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "user": user_data,
    }


@router.post("/register", response_model=schemas.User)
def register_user(
    user_in: schemas.UserCreate, db: Session = Depends(deps.get_db)
) -> Any:
    """
    注册新用户
    """
    # 检查用户名是否已存在
    user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    
    # 检查邮箱是否已存在
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在",
        )
    
    # 创建新用户
    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        department="未分配",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 为新用户分配默认角色
    add_role_for_user(str(user.id), "user")
    
    return user


@router.post("/logout")
def logout() -> Any:
    """
    登出
    """
    return {"message": "登出成功"}


@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取当前用户信息
    """
    return current_user 