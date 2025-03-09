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
        ehr_id="8765432",
        name="Normal User",
        is_active=True,
        is_superuser=False
    )

# 覆盖依赖
app.dependency_overrides[get_current_active_user] = get_test_admin

# 测试数据
test_approval_data = {
    "workflow_id": 1,
    "node_id": 1,
    "requester_id": 2,
    "status": "pending",
    "comment": "请审批这个工作流"
}

test_approval_review_data = {
    "status": "approved",
    "comment": "同意审批"
}

created_approval_id = None

def test_get_pending_tasks():
    """测试获取待办任务"""
    response = client.get("/api/v1/approvals/tasks")
    
    print(f"获取待办任务响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"发现 {len(result)} 个待办任务")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_approval_ledgers():
    """测试获取需要审批的台账列表"""
    response = client.get("/api/v1/approvals/ledgers")
    
    print(f"获取需要审批的台账列表响应: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"发现 {len(result)} 个待审批台账")
    
    assert response.status_code in [200, 403]
    if response.status_code == 200:
        assert isinstance(response.json(), list)

def test_submit_ledger_for_approval():
    """测试提交台账审批"""
    # 获取台账列表
    ledgers_response = client.get("/api/v1/ledgers/")
    if ledgers_response.status_code == 200 and len(ledgers_response.json()) > 0:
        ledger_id = ledgers_response.json()[0]["id"]
        
        # 获取工作流列表
        workflows_response = client.get("/api/v1/workflows/")
        if workflows_response.status_code == 200 and len(workflows_response.json()) > 0:
            workflow_id = workflows_response.json()[0]["id"]
            
            # 提交审批
            response = client.post(
                f"/api/v1/approvals/ledgers/{ledger_id}/submit",
                json={"workflow_id": workflow_id}
            )
            
            print(f"提交台账审批响应: {response.status_code}")
            
            assert response.status_code in [200, 400, 404, 422]
        else:
            print("找不到可用的工作流，跳过此测试")
    else:
        print("找不到可用的台账，跳过此测试")

def test_approve_ledger():
    """测试审批台账"""
    # 获取待办任务
    tasks_response = client.get("/api/v1/approvals/tasks")
    
    if tasks_response.status_code == 200 and len(tasks_response.json()) > 0:
        task = tasks_response.json()[0]
        ledger_id = task.get("ledger_id")
        
        if ledger_id:
            # 审批通过
            response = client.post(
                f"/api/v1/approvals/ledgers/{ledger_id}/approve",
                json={
                    "action": "approve",
                    "comment": "测试审批通过"
                }
            )
            
            print(f"审批台账响应: {response.status_code}")
            
            assert response.status_code in [200, 400, 404, 422]
    else:
        print("无待办任务，跳过此测试")

def test_reject_ledger():
    """测试拒绝台账"""
    # 提交新台账用于拒绝测试
    test_submit_ledger_for_approval()
    
    # 获取待办任务
    tasks_response = client.get("/api/v1/approvals/tasks")
    
    if tasks_response.status_code == 200 and len(tasks_response.json()) > 0:
        task = tasks_response.json()[0]
        ledger_id = task.get("ledger_id")
        
        if ledger_id:
            # 审批拒绝
            response = client.post(
                f"/api/v1/approvals/ledgers/{ledger_id}/approve",
                json={
                    "action": "reject",
                    "comment": "测试审批拒绝"
                }
            )
            
            print(f"拒绝台账响应: {response.status_code}")
            
            assert response.status_code in [200, 400, 404, 422]
    else:
        print("无待办任务，跳过此测试")

def test_get_workflow_instance():
    """测试获取工作流实例"""
    # 先尝试获取台账列表
    ledgers_response = client.get("/api/v1/ledgers/")
    
    if ledgers_response.status_code == 200 and len(ledgers_response.json()) > 0:
        ledger_id = ledgers_response.json()[0]["id"]
        
        # 获取台账的工作流实例
        response = client.get(f"/api/v1/approvals/workflow-instances/ledger/{ledger_id}")
        
        print(f"获取工作流实例响应: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"工作流实例信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        assert response.status_code in [200, 404]
    else:
        print("找不到可用的台账，跳过此测试")

def test_normal_user_approval_permissions():
    """测试普通用户的审批权限"""
    # 临时覆盖依赖
    original_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = get_normal_user
    
    try:
        # 普通用户尝试获取待办任务
        response = client.get("/api/v1/approvals/tasks")
        print(f"普通用户获取待办任务响应: {response.status_code}")
        # 所有用户都应该能看到自己的待办任务
        assert response.status_code == 200
        
        # 普通用户尝试获取所有需要审批的台账
        response = client.get("/api/v1/approvals/ledgers")
        print(f"普通用户获取所有待审批台账响应: {response.status_code}")
        # 应该返回403或200(如果有审批权限)
        assert response.status_code in [200, 403]
    finally:
        # 恢复原来的覆盖
        app.dependency_overrides[get_current_active_user] = original_override

# 以下是主函数
if __name__ == "__main__":
    # 按照顺序执行测试
    print("\n===== 开始审批API完整测试 =====\n")
    
    print("\n----- 测试获取待办任务 -----")
    test_get_pending_tasks()
    
    print("\n----- 测试获取需要审批的台账列表 -----")
    test_get_approval_ledgers()
    
    print("\n----- 测试提交台账审批 -----")
    test_submit_ledger_for_approval()
    
    print("\n----- 测试审批台账 -----")
    test_approve_ledger()
    
    print("\n----- 测试拒绝台账 -----")
    test_reject_ledger()
    
    print("\n----- 测试获取工作流实例 -----")
    test_get_workflow_instance()
    
    print("\n----- 测试普通用户的审批权限 -----")
    test_normal_user_approval_permissions()
    
    print("\n===== 审批API完整测试结束 =====\n") 