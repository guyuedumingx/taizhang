from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, remove_role_for_user, get_roles_for_user

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户列表
    """
    # 检查权限
    if not deps.check_permissions("user", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    # 获取每个用户的角色
    for user in users:
        user.roles = get_roles_for_user(str(user.id))
    
    return users


@router.post("/", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新用户
    """
    # 检查权限
    if not deps.check_permissions("user", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查用户名是否已存在
    user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="用户名已存在",
        )
    
    # 检查邮箱是否已存在
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="邮箱已存在",
        )
    
    # 创建用户
    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        department=user_in.department,
        is_active=True,
        is_superuser=False,
        team_id=user_in.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 为用户分配角色
    if user_in.role:
        add_role_for_user(str(user.id), user_in.role)
    else:
        # 默认角色为普通用户
        add_role_for_user(str(user.id), "user")
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户详情
    """
    # 检查权限
    if not deps.check_permissions("user", "view", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新用户信息
    """
    # 检查权限
    if not deps.check_permissions("user", "edit", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新用户信息
    update_data = user_in.dict(exclude_unset=True)
    
    # 如果更新密码，需要哈希处理
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    
    # 更新角色
    if "role" in update_data:
        role = update_data.pop("role")
        # 获取当前角色
        current_roles = get_roles_for_user(str(user.id))
        # 删除所有当前角色
        for current_role in current_roles:
            remove_role_for_user(str(user.id), current_role)
        # 添加新角色
        add_role_for_user(str(user.id), role)
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.delete("/{user_id}", response_model=schemas.User)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除用户
    """
    # 检查权限
    if not deps.check_permissions("user", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    # 不能删除超级管理员
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")
    
    # 删除用户
    db.delete(user)
    db.commit()
    
    return user 