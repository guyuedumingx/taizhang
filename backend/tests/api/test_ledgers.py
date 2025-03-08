import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api.deps import get_db, get_current_active_user
from app import models
from app.core.security import create_access_token

client = TestClient(app)

# 模拟当前用户
def get_test_user():
    return models.User(
        id=1,
        username="testuser",
        ehr_id="1234567",
        name="Test User",
        is_active=True,
        is_superuser=True
    )

# 覆盖依赖
app.dependency_overrides[get_current_active_user] = get_test_user

def test_read_ledgers():
    response = client.get("/api/v1/ledgers/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_export_ledger():
    # 测试导出单个台账
    response = client.get("/api/v1/ledgers/1/export?format=csv")
    # 即使台账不存在，权限检查应该通过
    assert response.status_code in [200, 404, 422]
    
    if response.status_code == 404:
        assert response.json()["detail"] == "台账不存在"

def test_export_all_ledgers():
    # 测试导出所有台账
    response = client.get("/api/v1/ledgers/export-all?format=csv")
    # 即使没有台账，权限检查应该通过
    assert response.status_code in [200, 404, 422]
    
    if response.status_code == 404:
        assert response.json()["detail"] == "没有找到符合条件的台账"

def test_export_ledger_permission():
    # 创建一个没有导出权限的用户
    def get_user_without_export_permission():
        return models.User(
            id=2,
            username="noexport",
            ehr_id="7654321",
            name="No Export User",
            is_active=True,
            is_superuser=False
        )
    
    # 临时覆盖依赖
    original_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = get_user_without_export_permission
    
    try:
        # 测试导出单个台账
        response = client.get("/api/v1/ledgers/1/export?format=csv")
        assert response.status_code == 403
        assert response.json()["detail"] == "没有足够的权限"
        
        # 测试导出所有台账
        response = client.get("/api/v1/ledgers/export-all?format=csv")
        assert response.status_code in [403, 422]
        assert response.json()["detail"] == "没有足够的权限"
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override 