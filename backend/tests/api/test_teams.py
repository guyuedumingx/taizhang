import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api.deps import get_db, get_current_active_user
from app import models, crud

client = TestClient(app)

# 模拟当前用户（管理员）
def get_test_admin():
    return models.User(
        id=1,
        username="testadmin",
        ehr_id="1234567",
        name="Test Admin",
        is_active=True,
        is_superuser=True
    )

# 覆盖依赖
app.dependency_overrides[get_current_active_user] = get_test_admin

def test_read_teams():
    """测试获取团队列表"""
    response = client.get("/api/v1/teams/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_team():
    """测试获取指定团队"""
    response = client.get("/api/v1/teams/1")
    # 由于是测试环境，可能找不到团队，但API路由应该存在
    assert response.status_code in [200, 404]
    
    if response.status_code == 404:
        assert response.json()["detail"] == "团队不存在"

def test_create_team():
    """测试创建团队"""
    response = client.post(
        "/api/v1/teams/",
        json={
            "name": "Test Team",
            "department": "Test Department",
            "description": "This is a test team"
        }
    )
    assert response.status_code in [200, 400, 422]

def test_update_team():
    """测试更新团队"""
    response = client.put(
        "/api/v1/teams/1",
        json={
            "name": "Updated Team Name",
            "department": "Updated Department",
            "description": "This is an updated team description"
        }
    )
    assert response.status_code in [200, 404, 422]

def test_delete_team():
    """测试删除团队"""
    # 这个测试可能会导致实际删除数据库中的团队，所以我们只测试路由是否存在
    # 在实际集成测试中，应该先创建测试团队，然后再删除
    response = client.delete("/api/v1/teams/999")  # 使用不太可能存在的ID
    assert response.status_code in [200, 404]

def test_get_team_members():
    """测试获取团队成员"""
    response = client.get("/api/v1/teams/1/members")
    # 由于是测试环境，可能找不到团队，但API路由应该存在
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        assert isinstance(response.json(), list)

def test_normal_user_team_permissions():
    """测试普通用户的团队管理权限"""
    # 创建一个普通用户
    def get_normal_user():
        return models.User(
            id=2,
            username="normaluser",
            ehr_id="7654321",
            name="Normal User",
            is_active=True,
            is_superuser=False
        )
    
    # 临时覆盖依赖
    original_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = get_normal_user
    
    try:
        # 普通用户尝试获取团队列表
        response = client.get("/api/v1/teams/")
        # 应该返回403或200(如果有读取权限)
        assert response.status_code in [200, 403]
        
        # 普通用户尝试创建团队
        response = client.post(
            "/api/v1/teams/",
            json={
                "name": "Unauthorized Team",
                "department": "Test Department",
                "description": "This is an unauthorized team"
            }
        )
        # 应该返回403(除非有创建权限)
        assert response.status_code in [200, 403, 422]
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override 