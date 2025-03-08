from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Team])
def read_teams(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取团队列表
    """
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    teams = db.query(models.Team).offset(skip).limit(limit).all()
    
    # 计算每个团队的成员数量
    for team in teams:
        team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
        
        # 获取团队负责人姓名
        if team.leader_id:
            leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
            team.leader_name = leader.name if leader else None
        else:
            team.leader_name = None
    
    return teams


@router.post("/", response_model=schemas.Team)
def create_team(
    *,
    db: Session = Depends(deps.get_db),
    team_in: schemas.TeamCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新团队
    """
    # 检查权限
    if not deps.check_permissions("team", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查团队名称是否已存在
    team = db.query(models.Team).filter(models.Team.name == team_in.name).first()
    if team:
        raise HTTPException(
            status_code=400,
            detail="团队名称已存在",
        )
    
    # 创建团队
    team = models.Team(
        name=team_in.name,
        department=team_in.department,
        description=team_in.description,
        leader_id=team_in.leader_id,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # 计算成员数量
    team.member_count = 0
    
    # 获取团队负责人姓名
    if team.leader_id:
        leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
        team.leader_name = leader.name if leader else None
    else:
        team.leader_name = None
    
    return team


@router.get("/{team_id}", response_model=schemas.Team)
def read_team(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取团队详情
    """
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    # 计算成员数量
    team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
    
    # 获取团队负责人姓名
    if team.leader_id:
        leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
        team.leader_name = leader.name if leader else None
    else:
        team.leader_name = None
    
    return team


@router.put("/{team_id}", response_model=schemas.Team)
def update_team(
    *,
    db: Session = Depends(deps.get_db),
    team_id: int,
    team_in: schemas.TeamUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新团队信息
    """
    # 检查权限
    if not deps.check_permissions("team", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    # 如果更新团队名称，检查是否已存在
    if team_in.name and team_in.name != team.name:
        existing_team = db.query(models.Team).filter(models.Team.name == team_in.name).first()
        if existing_team:
            raise HTTPException(
                status_code=400,
                detail="团队名称已存在",
            )
    
    # 更新团队信息
    update_data = team_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # 计算成员数量
    team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
    
    # 获取团队负责人姓名
    if team.leader_id:
        leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
        team.leader_name = leader.name if leader else None
    else:
        team.leader_name = None
    
    return team


@router.delete("/{team_id}", response_model=schemas.Team)
def delete_team(
    *,
    db: Session = Depends(deps.get_db),
    team_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除团队
    """
    # 检查权限
    if not deps.check_permissions("team", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    # 检查团队是否有成员
    member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
    if member_count > 0:
        raise HTTPException(status_code=400, detail="团队还有成员，不能删除")
    
    # 删除团队
    db.delete(team)
    db.commit()
    
    return team


@router.get("/{team_id}/members", response_model=List[schemas.User])
def read_team_members(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取团队成员列表
    """
    # 检查权限
    if not deps.check_permissions("team", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    members = db.query(models.User).filter(models.User.team_id == team.id).all()
    
    # 获取每个用户的角色
    for member in members:
        member.roles = deps.get_roles_for_user(str(member.id))
    
    return members 