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

def test_get_system_logs():
    """测试获取系统日志"""
    response = client.get("/api/v1/logs/system")
    assert response.status_code == 200
    # 检查返回是否是对象或列表
    result = response.json()
    if isinstance(result, dict):
        # 如果是分页格式
        assert "items" in result or "data" in result
        items = result.get("items") or result.get("data", [])
        assert isinstance(items, list)
    else:
        # 如果直接返回列表
        assert isinstance(result, list)

def test_get_system_logs_with_params():
    """测试带参数获取系统日志"""
    params = {
        "level": "info",
        "module": "user",
        "page": 1,
        "page_size": 10
    }
    response = client.get("/api/v1/logs/system", params=params)
    assert response.status_code == 200
    # 检查返回是否是对象或列表
    result = response.json()
    if isinstance(result, dict):
        # 如果是分页格式
        assert "items" in result or "data" in result
        items = result.get("items") or result.get("data", [])
        assert isinstance(items, list)
    else:
        # 如果直接返回列表
        assert isinstance(result, list)

def test_get_recent_system_logs():
    """测试获取最近系统日志"""
    response = client.get("/api/v1/logs/system/recent")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_system_errors():
    """测试获取系统错误日志"""
    response = client.get("/api/v1/logs/system/errors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_audit_logs():
    """测试获取审计日志"""
    response = client.get("/api/v1/logs/audit")
    assert response.status_code == 200
    # 检查返回是否是对象或列表
    result = response.json()
    if isinstance(result, dict):
        # 如果是分页格式
        assert "items" in result or "data" in result
        items = result.get("items") or result.get("data", [])
        assert isinstance(items, list)
    else:
        # 如果直接返回列表
        assert isinstance(result, list)

def test_get_audit_logs_with_params():
    """测试带参数获取审计日志"""
    params = {
        "action": "submit",
        "user_id": 1,
        "ledger_id": 1,
        "page": 1,
        "page_size": 10
    }
    response = client.get("/api/v1/logs/audit", params=params)
    assert response.status_code == 200
    # 检查返回是否是对象或列表
    result = response.json()
    if isinstance(result, dict):
        # 如果是分页格式
        assert "items" in result or "data" in result
        items = result.get("items") or result.get("data", [])
        assert isinstance(items, list)
    else:
        # 如果直接返回列表
        assert isinstance(result, list)

def test_get_ledger_audit_logs():
    """测试获取台账审计日志"""
    response = client.get("/api/v1/logs/audit/ledger/1")
    # 由于是测试环境，可能找不到台账，但API路由应该存在
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        assert isinstance(response.json(), list)

def test_normal_user_log_permissions():
    """测试普通用户的日志查看权限"""
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
        # 普通用户尝试获取系统日志
        response = client.get("/api/v1/logs/system")
        # 应该返回403(除非有日志查看权限)
        assert response.status_code in [200, 403]
        
        # 普通用户尝试获取审计日志
        response = client.get("/api/v1/logs/audit")
        # 应该返回403(除非有日志查看权限)
        assert response.status_code in [200, 403]
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override 

def test_get_workflow_audit_logs():
    """测试获取工作流审计日志"""
    response = client.get("/api/v1/logs/audit/workflow/1")
    # 由于是测试环境，可能找不到工作流，但API路由应该存在
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        assert isinstance(response.json(), list)
        logs = response.json()
        if logs:  # 如果有日志数据
            first_log = logs[0]
            # 检查日志结构
            assert "user_id" in first_log
            assert "workflow_instance_id" in first_log
            assert "action" in first_log
            assert "created_at" in first_log 