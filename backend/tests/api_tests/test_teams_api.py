import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_teams(db: Session, admin_token_headers: dict, team: models.Team):
    """测试获取团队列表"""
    response = client.get(
        f"{settings.API_V1_STR}/teams/",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 确认创建的测试团队在列表中
    assert any(t["id"] == team.id for t in data)


def test_create_team(db: Session, admin_token_headers: dict):
    """测试创建团队"""
    team_data = {
        "name": "测试API创建团队",
        "description": "通过API测试创建的团队",
        "department": "研发部门"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/teams/",
        headers=admin_token_headers,
        json=team_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == team_data["name"]
    assert data["description"] == team_data["description"]
    assert data["department"] == team_data["department"]
    
    # 清理测试数据
    team = db.query(models.Team).filter(models.Team.name == team_data["name"]).first()
    if team:
        db.delete(team)
        db.commit()


def test_get_team(db: Session, admin_token_headers: dict, team: models.Team):
    """测试获取单个团队详情"""
    response = client.get(
        f"{settings.API_V1_STR}/teams/{team.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == team.id
    assert data["name"] == team.name
    assert data["description"] == team.description
    assert data["department"] == team.department


def test_update_team(db: Session, admin_token_headers: dict, team: models.Team):
    """测试更新团队信息"""
    update_data = {
        "name": "已更新的团队名称",
        "description": "已更新的团队描述",
        "department": "已更新的部门"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/teams/{team.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == team.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["department"] == update_data["department"]


def test_delete_team(db: Session, admin_token_headers: dict):
    """测试删除团队"""
    # 先创建一个待删除的团队
    team_data = {
        "name": "待删除的测试团队",
        "description": "将被删除的测试团队",
        "department": "测试部门"
    }
    
    # 创建团队
    response = client.post(
        f"{settings.API_V1_STR}/teams/",
        headers=admin_token_headers,
        json=team_data,
    )
    assert response.status_code == 200
    team_id = response.json()["id"]
    
    # 删除团队
    response = client.delete(
        f"{settings.API_V1_STR}/teams/{team_id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证团队已被删除
    response = client.get(
        f"{settings.API_V1_STR}/teams/{team_id}",
        headers=admin_token_headers,
    )
    assert response.status_code == 404


def test_add_team_member(db: Session, admin_token_headers: dict, team: models.Team, normal_user: models.User):
    """测试添加团队成员"""
    member_data = {
        "user_id": normal_user.id,
        "role": "member"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/teams/{team.id}/members",
        headers=admin_token_headers,
        json=member_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team.id
    assert data["user_id"] == normal_user.id
    assert data["role"] == member_data["role"]
    
    # 清理测试数据
    team_member = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team.id,
        models.TeamMember.user_id == normal_user.id
    ).first()
    if team_member:
        db.delete(team_member)
        db.commit()


def test_get_team_members(db: Session, admin_token_headers: dict, team: models.Team):
    """测试获取团队成员列表"""
    response = client.get(
        f"{settings.API_V1_STR}/teams/{team.id}/members",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 团队成员可能为空，无法确定具体数量


def test_remove_team_member(db: Session, admin_token_headers: dict, team: models.Team, normal_user: models.User):
    """测试移除团队成员"""
    # 先添加团队成员
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=normal_user.id,
        role="member"
    )
    db.add(team_member)
    db.commit()
    
    # 移除团队成员
    response = client.delete(
        f"{settings.API_V1_STR}/teams/{team.id}/members/{normal_user.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证成员已被移除
    team_member = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team.id,
        models.TeamMember.user_id == normal_user.id
    ).first()
    assert team_member is None
