from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.models.role import Role
from app.services.role_service import role_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Role])
def read_roles(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    检索角色列表
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "role:view"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.get_roles(db, skip=skip, limit=limit)

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
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "role:create"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.create_role(db, role_in=role_in)

@router.get("/{role_id}", response_model=schemas.Role)
def read_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int = Path(..., title="角色ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取角色详情
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "role:view"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.get_role(db, role_id=role_id)

@router.put("/{role_id}", response_model=schemas.Role)
def update_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int = Path(..., title="角色ID"),
    role_in: schemas.RoleUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新角色
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "role:edit"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.update_role(db, role_id=role_id, role_in=role_in)

@router.delete("/{role_id}", response_model=schemas.Role)
def delete_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int = Path(..., title="角色ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除角色
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "role:delete"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.delete_role(db, role_id=role_id)

@router.get("/user/{user_id}/roles", response_model=List[str])
def read_user_roles(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int = Path(..., title="用户ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户的所有角色
    """
    # 检查是否有权限
    if not (crud.user.has_permission(db,current_user.id, "user:view") or current_user.id == user_id):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.get_user_roles(db, user_id=user_id)

@router.post("/user/{user_id}/roles/{role_name}", response_model=dict)
def add_user_role(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int = Path(..., title="用户ID"),
    role_name: str = Path(..., title="角色名称"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    为用户添加角色
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "user:edit"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.add_user_role(db, user_id=user_id, role_name=role_name)

@router.delete("/user/{user_id}/roles/{role_name}", response_model=dict)
def remove_user_role(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int = Path(..., title="用户ID"),
    role_name: str = Path(..., title="角色名称"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除用户的角色
    """
    # 检查是否有权限
    if not crud.user.has_permission(db,current_user.id, "user:edit"):
        raise HTTPException(status_code=403, detail="没有权限")
    
    return role_service.remove_user_role(db, user_id=user_id, role_name=role_name) 