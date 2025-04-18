import pytest
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.team_service import team_service


def test_get_teams(db: Session, team: models.Team):
    """测试获取团队列表"""
    # 再创建一个测试团队
    team_in = schemas.TeamCreate(
        name="测试团队2",
        description="这是测试团队2",
        department="测试部门2"
    )
    team2 = models.Team(
        name=team_in.name,
        description=team_in.description,
        department=team_in.department,
    )
    db.add(team2)
    db.commit()
    db.refresh(team2)
    
    # 测试获取所有团队
    teams = team_service.get_teams(db)
    assert len(teams) >= 2
    
    # 测试按名称搜索
    teams = team_service.get_teams(db, search="测试团队2")
    assert len(teams) == 1
    assert teams[0].name == "测试团队2"
    
    # 测试分页
    teams = team_service.get_teams(db, skip=1, limit=1)
    assert len(teams) == 1


def test_create_team(db: Session, normal_user: models.User):
    """测试创建团队"""
    # 创建测试数据
    team_in = schemas.TeamCreate(
        name="新团队",
        description="这是一个新团队",
        department="新部门"
    )
    
    # 创建团队
    team = team_service.create_team(db, team_in, normal_user.id)
    
    # 验证创建结果
    assert team.name == "新团队"
    assert team.description == "这是一个新团队"
    assert team.department == "新部门"
    assert team.leader_id == normal_user.id
    
    # 测试创建重复名称的团队
    with pytest.raises(Exception):
        team_service.create_team(db, team_in, normal_user.id)


def test_get_team(db: Session, team: models.Team):
    """测试获取单个团队"""
    # 获取团队
    got_team = team_service.get_team(db, team.id)
    
    # 验证结果
    assert got_team.id == team.id
    assert got_team.name == team.name
    assert got_team.description == team.description
    assert got_team.department == team.department
    
    # 测试不存在的团队
    with pytest.raises(Exception):
        team_service.get_team(db, 999)


def test_update_team(db: Session, team: models.Team, normal_user: models.User):
    """测试更新团队"""
    # 更新数据
    update_data = schemas.TeamUpdate(
        name="更新后的团队",
        description="更新后的描述",
        department="更新后的部门"
    )
    
    # 更新团队
    updated_team = team_service.update_team(db, team.id, update_data, normal_user.id)
    
    # 验证更新结果
    assert updated_team.id == team.id
    assert updated_team.name == "更新后的团队"
    assert updated_team.description == "更新后的描述"
    assert updated_team.department == "更新后的部门"
    
    # 测试不存在的团队
    with pytest.raises(Exception):
        team_service.update_team(db, 999, update_data, normal_user.id)


def test_delete_team(db: Session, normal_user: models.User):
    """测试删除团队"""
    # 创建测试团队
    team_in = schemas.TeamCreate(
        name="待删除团队",
        description="这是待删除的团队",
        department="测试部门"
    )
    team = team_service.create_team(db, team_in, normal_user.id)
    
    # 删除团队
    deleted_team = team_service.delete_team(db, team.id, normal_user.id)
    
    # 确认团队已被删除
    with pytest.raises(Exception):
        team_service.get_team(db, team.id)
    
    # 测试删除不存在的团队
    with pytest.raises(Exception):
        team_service.delete_team(db, 999, normal_user.id)


def test_get_team_members(db: Session, team: models.Team, normal_user: models.User):
    """测试获取团队成员"""
    # 获取团队成员
    members = team_service.get_team_members(db, team.id)
    
    # 验证结果
    assert len(members) >= 1
    assert any(member.id == normal_user.id for member in members)
    
    # 测试不存在的团队
    members_of_nonexistent_team = team_service.get_team_members(db, 999)
    assert len(members_of_nonexistent_team) == 0


def test_add_user_to_team(db: Session, team: models.Team, normal_user: models.User):
    """测试添加用户到团队"""
    # 创建一个新用户
    user_in = schemas.UserCreate(
        username="teamuser",
        ehr_id="1234568",  # 确保是7位数字
        password="password123",
        name="团队成员",
        department="测试部门",
    )
    user = models.User(
        username=user_in.username,
        ehr_id=user_in.ehr_id,
        hashed_password="hashed_password",  # 简化测试，不做实际哈希
        name=user_in.name,
        department=user_in.department,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 添加用户到团队
    updated_team = team_service.add_user_to_team(db, team.id, user.id, normal_user.id)
    
    # 验证结果
    db.refresh(user)
    assert user.team_id == team.id
    
    # 测试重复添加
    with pytest.raises(Exception):
        team_service.add_user_to_team(db, team.id, user.id, normal_user.id)
    
    # 测试不存在的团队
    with pytest.raises(Exception):
        team_service.add_user_to_team(db, 999, user.id, normal_user.id)
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        team_service.add_user_to_team(db, team.id, 999, normal_user.id)


def test_remove_user_from_team(db: Session, team: models.Team, normal_user: models.User):
    """测试从团队移除用户"""
    # 创建一个新用户并添加到团队
    user_in = schemas.UserCreate(
        username="teamuser2",
        ehr_id="1234569",  # 确保是7位数字
        password="password123",
        name="团队成员2",
        department="测试部门",
    )
    user = models.User(
        username=user_in.username,
        ehr_id=user_in.ehr_id,
        hashed_password="hashed_password",  # 简化测试，不做实际哈希
        name=user_in.name,
        department=user_in.department,
        is_active=True,
        is_superuser=False,
        team_id=team.id  # 直接添加到团队
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 从团队移除用户
    updated_team = team_service.remove_user_from_team(db, team.id, user.id, normal_user.id)
    
    # 验证结果
    db.refresh(user)
    assert user.team_id is None
    
    # 测试移除不在团队中的用户
    with pytest.raises(Exception):
        team_service.remove_user_from_team(db, team.id, user.id, normal_user.id)
    
    # 测试不存在的团队
    with pytest.raises(Exception):
        team_service.remove_user_from_team(db, 999, user.id, normal_user.id)
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        team_service.remove_user_from_team(db, team.id, 999, normal_user.id) 