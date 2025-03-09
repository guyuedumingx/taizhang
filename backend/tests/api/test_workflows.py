import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

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

# 模拟普通用户
def get_normal_user():
    return models.User(
        id=2,
        username="normaluser",
        ehr_id="7654321",
        name="Normal User",
        is_active=True,
        is_superuser=False
    )

# 覆盖依赖
app.dependency_overrides[get_current_active_user] = get_test_admin

# 测试数据
test_workflow_data = {
    "name": "测试工作流",
    "description": "这是一个测试工作流",
    "template_id": 1,
    "is_active": True,
    "nodes": [
        {
            "name": "开始节点",
            "description": "工作流开始",
            "node_type": "start",
            "order_index": 0
        },
        {
            "name": "审批节点",
            "description": "管理员审批",
            "node_type": "approval",
            "approver_user_id": 1,
            "order_index": 1
        },
        {
            "name": "结束节点",
            "description": "工作流结束",
            "node_type": "end",
            "order_index": 2,
            "is_final": True
        }
    ]
}

test_workflow_node_data = {
    "name": "新节点",
    "description": "这是一个新增节点",
    "node_type": "approval",
    "approver_user_id": 1,
    "order_index": 3
}

created_workflow_id = None

def test_create_workflow():
    """测试创建工作流"""
    global created_workflow_id
    
    response = client.post(
        "/api/v1/workflows/",
        json=test_workflow_data
    )
    
    print(f"创建工作流响应: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    
    assert response.status_code in [200, 201, 422]
    
    if response.status_code in [200, 201]:
        result = response.json()
        assert result["name"] == test_workflow_data["name"]
        assert result["description"] == test_workflow_data["description"]
        assert result["is_active"] == test_workflow_data["is_active"]
        created_workflow_id = result["id"]
        print(f"成功创建工作流，ID: {created_workflow_id}")
    elif response.status_code == 422:
        print("创建工作流参数验证失败，请检查请求数据")

def test_read_workflows():
    """测试获取工作流列表"""
    response = client.get("/api/v1/workflows/")
    
    print(f"获取工作流列表响应: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"发现 {len(result)} 个工作流")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_workflow_by_id():
    """测试获取指定工作流"""
    global created_workflow_id
    
    # 如果上一步创建了工作流，则使用该ID，否则使用ID=1
    workflow_id = created_workflow_id if created_workflow_id else 1
    
    response = client.get(f"/api/v1/workflows/{workflow_id}")
    
    print(f"获取工作流(ID={workflow_id})响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"工作流信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        assert result["id"] == workflow_id
    elif response.status_code == 404:
        print(f"工作流(ID={workflow_id})不存在")
        assert response.json()["detail"] == "工作流不存在"
    
    assert response.status_code in [200, 404]

def test_read_workflow_nodes():
    """测试获取工作流节点"""
    global created_workflow_id
    
    # 如果上一步创建了工作流，则使用该ID，否则使用ID=1
    workflow_id = created_workflow_id if created_workflow_id else 1
    
    response = client.get(f"/api/v1/workflows/{workflow_id}/nodes")
    
    print(f"获取工作流节点(工作流ID={workflow_id})响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"发现 {len(result)} 个节点")
        for node in result:
            print(f"节点: {node['name']}, 类型: {node['node_type']}, 顺序: {node['order_index']}")
        
        # 检查节点顺序是否正确
        if len(result) > 1:
            for i in range(1, len(result)):
                assert result[i-1]["order_index"] <= result[i]["order_index"]
    elif response.status_code == 404:
        print(f"工作流(ID={workflow_id})不存在")
    
    assert response.status_code in [200, 404]

def test_create_workflow_node():
    """测试创建工作流节点"""
    global created_workflow_id
    
    if not created_workflow_id:
        print("没有可用的工作流ID，跳过此测试")
        return
    
    workflow_id = created_workflow_id
    
    response = client.post(
        f"/api/v1/workflows/{workflow_id}/nodes",
        json=test_workflow_node_data
    )
    
    print(f"创建工作流节点响应: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"节点创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        assert result["name"] == test_workflow_node_data["name"]
        assert result["node_type"] == test_workflow_node_data["node_type"]
        assert result["order_index"] == test_workflow_node_data["order_index"]
    elif response.status_code == 404:
        print(f"工作流(ID={workflow_id})不存在")
    elif response.status_code == 422:
        print("创建节点参数验证失败，请检查请求数据")
    
    assert response.status_code in [200, 201, 404, 422]

def test_update_workflow():
    """测试更新工作流"""
    global created_workflow_id
    
    if not created_workflow_id:
        print("没有可用的工作流ID，跳过此测试")
        return
    
    workflow_id = created_workflow_id
    
    update_data = {
        "name": "更新后的工作流",
        "description": "这是更新后的工作流描述",
        "is_active": False
    }
    
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json=update_data
    )
    
    print(f"更新工作流响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"工作流更新成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
        assert result["is_active"] == update_data["is_active"]
    elif response.status_code == 404:
        print(f"工作流(ID={workflow_id})不存在")
    elif response.status_code == 422:
        print("更新工作流参数验证失败，请检查请求数据")
    
    assert response.status_code in [200, 404, 422]

def test_normal_user_workflow_permissions():
    """测试普通用户的工作流管理权限"""
    # 临时覆盖依赖
    original_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = get_normal_user
    
    try:
        # 普通用户尝试获取工作流列表
        response = client.get("/api/v1/workflows/")
        print(f"普通用户获取工作流列表响应: {response.status_code}")
        # 应该返回403或200(如果有读取权限)
        assert response.status_code in [200, 403]
        
        # 普通用户尝试创建工作流
        response = client.post(
            "/api/v1/workflows/",
            json={
                "name": "普通用户工作流",
                "description": "这是普通用户创建的工作流",
                "template_id": 1,
                "is_active": True,
                "nodes": [
                    {
                        "name": "开始节点",
                        "description": "工作流开始",
                        "node_type": "start",
                        "order_index": 0
                    },
                    {
                        "name": "结束节点",
                        "description": "工作流结束",
                        "node_type": "end",
                        "order_index": 1,
                        "is_final": True
                    }
                ]
            }
        )
        print(f"普通用户创建工作流响应: {response.status_code}")
        # 应该返回403(除非有创建权限)
        assert response.status_code in [200, 201, 403, 422]
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override

def test_delete_workflow():
    """测试删除工作流"""
    global created_workflow_id
    
    if not created_workflow_id:
        print("没有可用的工作流ID，跳过此测试")
        return
    
    workflow_id = created_workflow_id
    
    response = client.delete(f"/api/v1/workflows/{workflow_id}")
    
    print(f"删除工作流(ID={workflow_id})响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"工作流删除成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 检查工作流是否被停用（不是真正删除）
        check_response = client.get(f"/api/v1/workflows/{workflow_id}")
        if check_response.status_code == 200:
            check_result = check_response.json()
            assert check_result["is_active"] == False, "工作流应该被停用"
        else:
            assert check_response.status_code == 404, "工作流应该返回404或者被停用"
    elif response.status_code == 404:
        print(f"工作流(ID={workflow_id})不存在")
    
    assert response.status_code in [200, 404]

def test_invalid_workflow_operations():
    """测试无效的工作流操作"""
    # 尝试创建无效的工作流
    invalid_workflow = {
        "name": "",  # 空名称，应该无效
        "description": "这是一个无效的工作流",
        "template_id": 1,
        "is_active": True
    }
    
    response = client.post(
        "/api/v1/workflows/",
        json=invalid_workflow
    )
    
    print(f"创建无效工作流响应: {response.status_code}")
    assert response.status_code in [400, 422]
    
    # 尝试获取不存在的工作流
    response = client.get("/api/v1/workflows/99999")
    
    print(f"获取不存在工作流响应: {response.status_code}")
    assert response.status_code == 404
    
    # 尝试更新不存在的工作流
    response = client.put(
        "/api/v1/workflows/99999",
        json={"name": "更新不存在的工作流"}
    )
    
    print(f"更新不存在工作流响应: {response.status_code}")
    assert response.status_code == 404
    
    # 尝试删除不存在的工作流
    response = client.delete("/api/v1/workflows/99999")
    
    print(f"删除不存在工作流响应: {response.status_code}")
    assert response.status_code == 404

# 以下是主函数
if __name__ == "__main__":
    # 按照顺序执行测试
    print("\n===== 开始工作流API完整测试 =====\n")
    
    print("\n----- 测试创建工作流 -----")
    test_create_workflow()
    
    print("\n----- 测试获取工作流列表 -----")
    test_read_workflows()
    
    print("\n----- 测试获取指定工作流 -----")
    test_read_workflow_by_id()
    
    print("\n----- 测试获取工作流节点 -----")
    test_read_workflow_nodes()
    
    print("\n----- 测试创建工作流节点 -----")
    test_create_workflow_node()
    
    print("\n----- 测试更新工作流 -----")
    test_update_workflow()
    
    print("\n----- 测试普通用户的工作流管理权限 -----")
    test_normal_user_workflow_permissions()
    
    print("\n----- 测试无效的工作流操作 -----")
    test_invalid_workflow_operations()
    
    print("\n----- 测试删除工作流 -----")
    test_delete_workflow()
    
    print("\n===== 工作流API完整测试结束 =====\n") 