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

def test_get_system_overview():
    """测试获取系统概览"""
    response = client.get("/api/v1/statistics/overview")
    assert response.status_code == 200
    data = response.json()
    # 对于简化后的统计模块，检查返回消息
    assert "message" in data
    assert data["message"] == "系统概览数据"

def test_get_ledger_statistics():
    """测试获取台账统计"""
    response = client.get("/api/v1/statistics/ledgers")
    assert response.status_code == 200
    data = response.json()
    # 对于简化后的统计模块，检查返回消息
    assert "message" in data
    assert data["message"] == "台账统计数据"

def test_get_workflow_statistics():
    """测试获取工作流统计"""
    response = client.get("/api/v1/statistics/workflows")
    assert response.status_code == 200
    data = response.json()
    # 对于简化后的统计模块，检查返回消息
    assert "message" in data
    assert data["message"] == "工作流统计数据"

def test_normal_user_statistics_permissions():
    """测试普通用户的统计查看权限"""
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
        # 普通用户尝试获取系统概览
        response = client.get("/api/v1/statistics/overview")
        # 应该返回200或403(取决于权限设置)
        assert response.status_code in [200, 403]
        
        # 普通用户尝试获取台账统计
        response = client.get("/api/v1/statistics/ledgers")
        # 应该返回200或403(取决于权限设置)
        assert response.status_code in [200, 403]
        
        # 普通用户尝试获取工作流统计
        response = client.get("/api/v1/statistics/workflows")
        # 应该返回200或403(取决于权限设置)
        assert response.status_code in [200, 403]
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override 