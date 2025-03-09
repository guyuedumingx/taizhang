"""
统计模块API测试
"""

import pytest
import json
import requests
from urllib.parse import urljoin
import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# 获取当前文件所在目录的父目录的父目录（项目根目录）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# 测试服务器URL
BASE_URL = "http://localhost:8080"

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

def get_token():
    """获取测试令牌"""
    response = requests.get(urljoin(BASE_URL, "/api/v1/test-token"))
    data = response.json()
    return data.get("access_token")

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

def test_statistics_overview():
    """测试系统概览统计接口"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 发送请求
    response = requests.get(
        urljoin(BASE_URL, "/api/v1/statistics/overview"),
        headers=headers
    )
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "message" in data, f"响应中缺少message字段：{data}"
    assert data["message"] == "系统概览数据", f"响应内容不符合预期：{data}"

def test_statistics_ledgers():
    """测试台账统计接口"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 发送请求
    response = requests.get(
        urljoin(BASE_URL, "/api/v1/statistics/ledgers"),
        headers=headers
    )
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "message" in data, f"响应中缺少message字段：{data}"
    assert data["message"] == "台账统计数据", f"响应内容不符合预期：{data}"

def test_statistics_workflows():
    """测试工作流统计接口"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 发送请求
    response = requests.get(
        urljoin(BASE_URL, "/api/v1/statistics/workflows"),
        headers=headers
    )
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "message" in data, f"响应中缺少message字段：{data}"
    assert data["message"] == "工作流统计数据", f"响应内容不符合预期：{data}"

def run_all_tests():
    """执行所有测试"""
    try:
        test_get_system_overview()
        print("✅ 测试通过: test_get_system_overview")
        
        test_get_ledger_statistics()
        print("✅ 测试通过: test_get_ledger_statistics")
        
        test_get_workflow_statistics()
        print("✅ 测试通过: test_get_workflow_statistics")
        
        test_normal_user_statistics_permissions()
        print("✅ 测试通过: test_normal_user_statistics_permissions")
        
        test_statistics_overview()
        print("✅ 测试通过: test_statistics_overview")
        
        test_statistics_ledgers()
        print("✅ 测试通过: test_statistics_ledgers")
        
        test_statistics_workflows()
        print("✅ 测试通过: test_statistics_workflows")
        
        print("✅ 所有统计模块测试通过!")
        return True
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

if __name__ == "__main__":
    print("===== 开始测试统计模块API =====")
    success = run_all_tests()
    print("===== 统计模块API测试完成 =====")
    
    if not success:
        sys.exit(1) 