from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services.casbin_service import (
    get_roles_for_user, 
    get_permissions_for_role, 
    add_role_for_user, 
    remove_role_for_user,
    add_permission_for_role,
    remove_permission_for_role
)

router = APIRouter()


@router.get("/", response_model=List[schemas.Role])
def read_roles(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取角色列表
    """
    # 检查权限
    if not deps.check_permissions("role", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取所有角色
    roles = db.query(models.Role).all()
    
    # 获取每个角色的权限
    for role in roles:
        permissions = get_permissions_for_role(role.name)
        # 转换权限格式
        role.permissions = []
        for p in permissions:
            if len(p) >= 3:
                role.permissions.append(f"{p[1]}:{p[2]}")
    
    return roles


@router.post("/", response_model=schemas.Role)
def create_role(
    *,
    db: Session = Depends(deps.get_db),
    role_in: schemas.RoleCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新角色
    """
    # 检查权限
    if not deps.check_permissions("role", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查角色名称是否已存在
    role = db.query(models.Role).filter(models.Role.name == role_in.name).first()
    if role:
        raise HTTPException(
            status_code=400,
            detail="角色名称已存在",
        )
    
    # 创建角色
    role = models.Role(
        name=role_in.name,
        description=role_in.description,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    
    # 添加权限
    if role_in.permissions:
        for permission in role_in.permissions:
            resource, action = permission.split(":")
            add_permission_for_role(role.name, resource, action)
    
    # 获取角色权限
    permissions = get_permissions_for_role(role.name)
    # 转换权限格式
    role.permissions = []
    for p in permissions:
        if len(p) >= 3:
            role.permissions.append(f"{p[1]}:{p[2]}")
    
    return role


@router.get("/{role_id}", response_model=schemas.Role)
def read_role(
    role_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取角色详情
    """
    # 检查权限
    if not deps.check_permissions("role", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 获取角色权限
    permissions = get_permissions_for_role(role.name)
    # 转换权限格式
    role.permissions = []
    for p in permissions:
        if len(p) >= 3:
            role.permissions.append(f"{p[1]}:{p[2]}")
    
    return role


@router.put("/{role_id}", response_model=schemas.Role)
def update_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int,
    role_in: schemas.RoleUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新角色信息
    """
    # 检查权限
    if not deps.check_permissions("role", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 如果更新角色名称，检查是否已存在
    if role_in.name and role_in.name != role.name:
        existing_role = db.query(models.Role).filter(models.Role.name == role_in.name).first()
        if existing_role:
            raise HTTPException(
                status_code=400,
                detail="角色名称已存在",
            )
    
    # 更新角色信息
    update_data = role_in.dict(exclude_unset=True)
    
    # 处理权限更新
    if "permissions" in update_data:
        permissions = update_data.pop("permissions")
        
        # 获取当前权限
        current_permissions = get_permissions_for_role(role.name)
        current_permission_strs = []
        
        for p in current_permissions:
            if len(p) >= 3:
                current_permission_strs.append(f"{p[1]}:{p[2]}")
        
        # 添加新权限
        for permission in permissions:
            if permission not in current_permission_strs:
                resource, action = permission.split(":")
                add_permission_for_role(role.name, resource, action)
        
        # 删除移除的权限
        for permission in current_permission_strs:
            if permission not in permissions:
                resource, action = permission.split(":")
                remove_permission_for_role(role.name, resource, action)
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(role, field, value)
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    # 获取更新后的权限
    permissions = get_permissions_for_role(role.name)
    # 转换权限格式
    role.permissions = []
    for p in permissions:
        if len(p) >= 3:
            role.permissions.append(f"{p[1]}:{p[2]}")
    
    return role


@router.delete("/{role_id}", response_model=schemas.Role)
def delete_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除角色
    """
    # 检查权限
    if not deps.check_permissions("role", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 检查是否为系统角色
    if role.name in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="不能删除系统角色")
    
    # 删除角色
    db.delete(role)
    db.commit()
    
    return role


@router.get("/user/{user_id}", response_model=List[str])
def read_user_roles(
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户的角色
    """
    # 检查权限
    if not deps.check_permissions("role", "view", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取用户角色
    roles = get_roles_for_user(str(user_id))
    
    return roles


@router.post("/user/{user_id}/roles", response_model=List[str])
def assign_role_to_user(
    *,
    user_id: int,
    role_name: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    为用户分配角色
    """
    # 检查权限
    if not deps.check_permissions("role", "assign", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查用户是否存在
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查角色是否存在
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 检查用户是否已有该角色
    user_roles = get_roles_for_user(str(user_id))
    if role_name in user_roles:
        raise HTTPException(status_code=400, detail="用户已有该角色")
    
    # 分配角色
    add_role_for_user(str(user_id), role_name)
    
    # 获取更新后的角色
    updated_roles = get_roles_for_user(str(user_id))
    
    return updated_roles


@router.delete("/user/{user_id}/roles/{role_name}", response_model=List[str])
def remove_role_from_user(
    *,
    user_id: int,
    role_name: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    移除用户的角色
    """
    # 检查权限
    if not deps.check_permissions("role", "assign", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查用户是否存在
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查角色是否存在
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 检查是否为系统角色
    if role_name == "user" and not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="不能移除基本用户角色")
    
    # 检查用户是否有该角色
    user_roles = get_roles_for_user(str(user_id))
    if role_name not in user_roles:
        raise HTTPException(status_code=400, detail="用户没有该角色")
    
    # 移除角色
    remove_role_for_user(str(user_id), role_name)
    
    # 获取更新后的角色
    updated_roles = get_roles_for_user(str(user_id))
    
    return updated_roles 