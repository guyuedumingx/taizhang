from typing import Generator, Optional, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import ValidationError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import get_password_change_requirement
from app.services.casbin_service import get_enforcer_instance, get_roles_for_user, get_permissions_for_role, check_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# 强制改密期间仍放行的端点: 改密本身 / 登出 / 自身信息 (前端弹窗渲染所需)。
# 其余一切业务 API 在改密完成前一律 403 (重构方案 Phase 0: 评审 P0-1)。
_PASSWORD_CHANGE_ALLOWED_PATHS = frozenset({
    f"{settings.API_V1_STR}/auth/change-password",
    f"{settings.API_V1_STR}/auth/logout",
    f"{settings.API_V1_STR}/auth/me",
    f"{settings.API_V1_STR}/auth/check-password-expired",
})


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    request: Request = None,
) -> models.User:
    """
    获取当前用户; 首次登录未改密 / 密码超 90 天未改时, 除放行端点外一律 403。
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")

    if request is not None and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS:
        requirement = get_password_change_requirement(db, user)
        if requirement == "PASSWORD_CHANGE_REQUIRED":
            raise HTTPException(
                status_code=403,
                detail="PASSWORD_CHANGE_REQUIRED: 首次登录必须先修改密码",
            )
        if requirement == "PASSWORD_EXPIRED":
            raise HTTPException(
                status_code=403,
                detail="PASSWORD_EXPIRED: 密码已超过90天未修改, 请先修改密码",
            )
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    获取当前激活用户
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    获取当前超级管理员用户
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="用户没有足够的权限"
        )
    return current_user


def check_permissions(
    resource: str, action: str, current_user: models.User = Depends(get_current_user)
) -> bool:
    """
    检查用户是否有权限执行操作
    """
    from app.services.casbin_service import check_permission
    
    # 超级管理员拥有所有权限
    if current_user.is_superuser:
        return True
    
    # 使用Casbin检查权限
    return check_permission(str(current_user.id), resource, action)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close() 