import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """测试根路径接口"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "台账管理系统API服务"

def test_health_endpoint():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "message" in data
    assert data["message"] == "服务正常运行"

def test_api_health_endpoint():
    """测试API V1健康检查接口"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_api_test_token_endpoint():
    """测试获取测试令牌接口"""
    response = client.get("/api/v1/test-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    # 检查令牌格式是否正确
    token = data["access_token"]
    assert len(token) > 0
    assert token.count('.') == 2  # JWT格式应有两个点分隔 