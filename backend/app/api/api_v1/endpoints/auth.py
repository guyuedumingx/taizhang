from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core.security import create_access_token, verify_password, get_password_hash
from app.services.casbin_service import get_roles_for_user, get_permissions_for_role, add_role_for_user

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    用户登录
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    
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
        "teamId": user.team_id
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
    
    # 检查EHR号是否已存在
    user = db.query(models.User).filter(models.User.ehr_id == user_in.ehr_id).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EHR号已存在",
        )
    
    # 创建新用户
    user = models.User(
        username=user_in.username,
        ehr_id=user_in.ehr_id,
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


@router.post("/check-password-expired", response_model=schemas.PasswordExpiredResponse)
def check_password_expired(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    检查当前用户的密码是否过期
    """
    password_expired = False
    if current_user.last_password_change:
        three_months_ago = datetime.now() - timedelta(days=90)
        password_expired = current_user.last_password_change < three_months_ago
    
    return {
        "password_expired": password_expired,
        "days_until_expiry": -1 if not password_expired else 0,  # 如果已过期，则为0
        "last_password_change": current_user.last_password_change
    }


@router.post("/change-password", response_model=schemas.PasswordChangeResponse)
def change_password(
    password_data: schemas.PasswordChange,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    修改当前用户的密码
    """
    # 验证当前密码
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    
    # 更新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.last_password_change = datetime.now()
    
    db.add(current_user)
    db.commit()
    
    return {"success": True, "message": "密码修改成功"} 