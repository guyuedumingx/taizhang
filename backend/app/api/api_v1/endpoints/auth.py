from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core.security import create_access_token, verify_password, get_password_hash
from app.services.casbin_service import get_roles_for_user, get_permissions_for_role, add_role_for_user
from app.services.user.auth_service import auth_service

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    用户登录 (使用EHR号)
    """
    return auth_service.authenticate_user(db, ehr_id=form_data.username, password=form_data.password)


@router.post("/register", response_model=schemas.User)
def register_user(
    user_in: schemas.UserCreate, db: Session = Depends(deps.get_db)
) -> Any:
    """
    注册新用户
    """
    return auth_service.register_user(db, user_in=user_in)


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

    days_until_expiry = 90
    if current_user.last_password_change:
        days_until_expiry = 90 - (datetime.now() - current_user.last_password_change).days
    
    return {
        "password_expired": password_expired,
        "days_until_expiry": days_until_expiry if not password_expired else 0,
        "last_password_change": current_user.last_password_change
    }


@router.post("/change-password", response_model=dict)
def change_password(
    *,
    db: Session = Depends(deps.get_db),
    password_data: schemas.PasswordChange,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    修改当前用户的密码
    """
    return auth_service.change_password(db, user_id=current_user.id, password_data=password_data) 