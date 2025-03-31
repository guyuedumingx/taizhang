import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_dashboard_statistics(db: Session, admin_token_headers: dict):
    """测试获取仪表盘统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/dashboard",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "user_count" in data
    assert "team_count" in data
    assert "template_count" in data
    assert "ledger_count" in data
    assert "monthly_ledgers" in data
    assert "approval_statistics" in data


def test_get_user_statistics(db: Session, admin_token_headers: dict):
    """测试获取用户统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/users",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "inactive_users" in data
    assert "new_users_by_month" in data
    assert isinstance(data["new_users_by_month"], list)


def test_get_ledger_statistics(db: Session, admin_token_headers: dict):
    """测试获取台账统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/ledgers",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_ledgers" in data
    assert "draft_ledgers" in data
    assert "active_ledgers" in data
    assert "completed_ledgers" in data
    assert "ledgers_by_month" in data
    assert isinstance(data["ledgers_by_month"], list)


def test_get_approval_statistics(db: Session, admin_token_headers: dict):
    """测试获取审批统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/approvals",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_approvals" in data
    assert "pending_approvals" in data
    assert "approved_approvals" in data
    assert "rejected_approvals" in data
    assert "approval_time_avg" in data
    assert "approvals_by_month" in data
    assert isinstance(data["approvals_by_month"], list)


def test_get_team_statistics(db: Session, admin_token_headers: dict):
    """测试获取团队统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/teams",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_teams" in data
    assert "team_member_counts" in data
    assert "ledgers_by_team" in data
    assert isinstance(data["team_member_counts"], dict)
    assert isinstance(data["ledgers_by_team"], dict)


def test_get_template_statistics(db: Session, admin_token_headers: dict):
    """测试获取模板统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/templates",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_templates" in data
    assert "templates_by_department" in data
    assert "templates_usage" in data
    assert isinstance(data["templates_by_department"], dict)
    assert isinstance(data["templates_usage"], dict)


def test_get_my_statistics(db: Session, normal_token_headers: dict):
    """测试获取当前用户的统计数据"""
    response = client.get(
        f"{settings.API_V1_STR}/statistics/my",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "ledgers_created" in data
    assert "pending_approvals" in data
    assert "completed_approvals" in data
    assert "recent_activities" in data
    assert isinstance(data["recent_activities"], list)
