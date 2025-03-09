from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    """
    获取当前用户
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


def get_roles_for_user(user_id: str):
    """
    获取用户的所有角色
    
    Args:
        user_id: 用户ID
    
    Returns:
        角色列表
    """
    from app.db.session import SessionLocal
    from app.models.user_role import UserRole
    from app.models.role import Role
    
    db = SessionLocal()
    try:
        # 查询用户角色关系
        user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
        
        # 获取角色名称
        role_ids = [ur.role_id for ur in user_roles]
        roles = db.query(Role.name).filter(Role.id.in_(role_ids)).all()
        
        # 返回角色名称列表
        return [role[0] for role in roles]
    except Exception as e:
        print(f"获取用户角色失败: {str(e)}")
        return []
    finally:
        db.close() 