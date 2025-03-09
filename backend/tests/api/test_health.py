"""
健康检查API测试
"""

import pytest
import json
import requests
from urllib.parse import urljoin
import os
import sys

# 获取当前文件所在目录的父目录的父目录（项目根目录）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# 测试服务器URL
BASE_URL = "http://localhost:8080"

def test_root_endpoint():
    """测试根接口"""
    response = requests.get(BASE_URL)
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "message" in data, f"响应中缺少message字段：{data}"
    assert data["message"] == "台账管理系统API服务", f"响应内容不符合预期：{data}"

def test_health_endpoint():
    """测试健康检查接口"""
    response = requests.get(urljoin(BASE_URL, "/health"))
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "status" in data, f"响应中缺少status字段：{data}"
    assert data["status"] == "ok", f"响应状态不符合预期：{data}"
    assert "message" in data, f"响应中缺少message字段：{data}"
    assert data["message"] == "服务正常运行", f"响应消息不符合预期：{data}"

def test_api_health_endpoint():
    """测试API健康检查接口"""
    response = requests.get(urljoin(BASE_URL, "/api/v1/health"))
    
    # 打印响应内容以便调试
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 检查响应状态码
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应：{response.text}"
    
    # 检查响应内容
    data = response.json()
    assert "status" in data, f"响应中缺少status字段：{data}"
    assert data["status"] == "ok", f"响应状态不符合预期：{data}"

def run_all_tests():
    """执行所有测试"""
    try:
        test_root_endpoint()
        print("✅ 测试通过: test_root_endpoint")
        
        test_health_endpoint()
        print("✅ 测试通过: test_health_endpoint")
        
        test_api_health_endpoint()
        print("✅ 测试通过: test_api_health_endpoint")
        
        print("✅ 所有健康检查接口测试通过!")
        return True
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

if __name__ == "__main__":
    print("===== 开始测试健康检查API =====")
    success = run_all_tests()
    print("===== 健康检查API测试完成 =====")
    
    if not success:
        sys.exit(1) 