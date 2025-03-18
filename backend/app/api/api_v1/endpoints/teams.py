from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services.team.team_service import team_service

router = APIRouter()


@router.get("/", response_model=List[schemas.Team])
def read_teams(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取团队列表"""
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.get_teams(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.Team)
def create_team(
    *,
    db: Session = Depends(deps.get_db),
    team_in: schemas.TeamCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """创建新团队"""
    # 检查权限
    if not deps.check_permissions("team", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.create_team(db, team_in=team_in)


@router.get("/{team_id}", response_model=schemas.Team)
def read_team(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取团队详情"""
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.get_team(db, team_id=team_id)


@router.put("/{team_id}", response_model=schemas.Team)
def update_team(
    *,
    db: Session = Depends(deps.get_db),
    team_id: int,
    team_in: schemas.TeamUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """更新团队信息"""
    # 检查权限
    if not deps.check_permissions("team", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.update_team(db, team_id=team_id, team_in=team_in)


@router.delete("/{team_id}", response_model=schemas.Team)
def delete_team(
    *,
    db: Session = Depends(deps.get_db),
    team_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """删除团队"""
    # 检查权限
    if not deps.check_permissions("team", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.delete_team(db, team_id=team_id)


@router.get("/{team_id}/members")
def read_team_members(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取团队成员列表"""
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return team_service.get_team_members(db, team_id=team_id) 