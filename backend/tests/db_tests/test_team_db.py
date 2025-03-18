import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas


def test_create_team(db: Session, test_team: dict):
    """测试创建团队"""
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    team = crud.team.create(db, obj_in=team_in)
    
    assert team.name == test_team["name"]
    assert team.description == test_team["description"]
    assert team.department == test_team["department"]


def test_get_team(db: Session, test_team: dict):
    """测试获取团队"""
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    created_team = crud.team.create(db, obj_in=team_in)
    
    fetched_team = crud.team.get(db, id=created_team.id)
    
    assert fetched_team
    assert fetched_team.id == created_team.id
    assert fetched_team.name == test_team["name"]
    assert fetched_team.description == test_team["description"]
    assert fetched_team.department == test_team["department"]


def test_get_team_by_name(db: Session, test_team: dict):
    """测试通过名称获取团队"""
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    crud.team.create(db, obj_in=team_in)
    
    fetched_team = crud.team.get_by_name(db, name=test_team["name"])
    
    assert fetched_team
    assert fetched_team.name == test_team["name"]
    assert fetched_team.description == test_team["description"]
    assert fetched_team.department == test_team["department"]


def test_update_team(db: Session, test_team: dict):
    """测试更新团队"""
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    created_team = crud.team.create(db, obj_in=team_in)
    
    new_description = "Updated description"
    
    team_update = schemas.TeamUpdate(
        description=new_description,
    )
    
    updated_team = crud.team.update(db, db_obj=created_team, obj_in=team_update)
    
    assert updated_team.id == created_team.id
    assert updated_team.name == created_team.name
    assert updated_team.description == new_description
    assert updated_team.department == created_team.department


def test_delete_team(db: Session, test_team: dict):
    """测试删除团队"""
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    created_team = crud.team.create(db, obj_in=team_in)
    team_id = created_team.id
    
    deleted_team = crud.team.remove(db, id=team_id)
    
    assert deleted_team.id == team_id
    
    # 确认团队已被删除
    fetched_team = crud.team.get(db, id=team_id)
    assert fetched_team is None


def test_get_multi_teams(db: Session, test_team: dict):
    """测试获取多个团队"""
    # 创建第一个团队
    team1_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    # 创建第二个团队
    team2_in = schemas.TeamCreate(
        name=f"{test_team['name']}_2",
        description=f"{test_team['description']} 2",
        department=f"{test_team['department']} 2",
    )
    
    crud.team.create(db, obj_in=team1_in)
    crud.team.create(db, obj_in=team2_in)
    
    teams = crud.team.get_multi(db, skip=0, limit=10)
    
    assert len(teams) >= 2
    assert any(team.name == team1_in.name for team in teams)
    assert any(team.name == team2_in.name for team in teams)


def test_get_team_members(db: Session, test_team: dict, test_user: dict):
    """测试获取团队成员"""
    # 创建团队
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        description=test_team["description"],
        department=test_team["department"],
    )
    
    team = crud.team.create(db, obj_in=team_in)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        password="password123",
        ehr_id=test_user["ehr_id"],
        name=test_user["name"],
        department=test_user["department"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 更新用户，设置team_id
    user_update = schemas.UserUpdate(team_id=team.id)
    updated_user = crud.user.update(db, db_obj=user, obj_in=user_update)
    
    # 获取团队成员
    team_members = crud.team.get_team_members(db, team_id=team.id)
    
    assert len(team_members) == 1
    assert team_members[0].id == user.id
    assert team_members[0].username == user.username 