from typing import Generator, Optional, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import ValidationError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.db.session import SessionLocal
from app.models.user import User
from app.services.casbin_service import get_enforcer_instance, get_roles_for_user, get_permissions_for_role, check_permission

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


# def get_roles_for_user(user_id: str):
#     """
#     获取用户的所有角色
    
#     Args:
#         user_id: 用户ID
    
#     Returns:
#         角色列表
#     """
#     from app.db.session import SessionLocal
#     from app.models.user_role import UserRole
#     from app.models.role import Role
    
#     db = SessionLocal()
#     try:
#         # 查询用户角色关系
#         user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
        
#         # 获取角色名称
#         role_ids = [ur.role_id for ur in user_roles]
#         roles = db.query(Role.name).filter(Role.id.in_(role_ids)).all()
        
#         # 返回角色名称列表
#         return [role[0] for role in roles]
#     except Exception as e:
#         print(f"获取用户角色失败: {str(e)}")
#         return []
#     finally:
#         db.close()


def convert_user_to_schema(user: User, db = None) -> schemas.User:
    """
    将数据库User模型转换为API User schema
    
    Args:
        user: 数据库User模型
        db: 数据库会话(可选,用于某些需要数据库的操作)
    
    Returns:
        schemas.User: 转换后的schema对象
    """
    if not user:
        return None
        
    # 获取用户角色
    roles = get_roles_for_user(str(user.id))
    
    # 使用fastapi.encoders来避免循环引用
    from fastapi.encoders import jsonable_encoder
    try:
        user_dict = jsonable_encoder(user)
        # 添加角色
        user_dict["roles"] = roles
        # 创建Pydantic模型
        user_model = schemas.User.model_validate(user_dict)
        
        # 为了测试目的，直接将hashed_password字段添加到模型
        if hasattr(user, 'hashed_password'):
            user_model.hashed_password = user.hashed_password
            
        return user_model
    except Exception as e:
        print(f"转换用户到Pydantic模型时出错: {e}")
        return None


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close() 