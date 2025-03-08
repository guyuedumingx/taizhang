import requests
import json
import time
from pprint import pprint

# API基础URL
BASE_URL = "http://localhost:8082/api/v1"

# 测试用户凭据
USERNAME = "admin"
PASSWORD = "admin123"

# 获取访问令牌
def get_access_token():
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.status_code}")
        print(response.text)
        return None

# 测试获取台账列表
def test_get_ledgers(token):
    url = f"{BASE_URL}/ledgers/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取台账列表成功")
        ledgers = response.json()
        print(f"台账数量: {len(ledgers)}")
        if ledgers:
            print("第一个台账:")
            pprint(ledgers[0])
        return True
    else:
        print(f"获取台账列表失败: {response.status_code}")
        print(response.text)
        return False

# 测试创建台账
def test_create_ledger(token):
    url = f"{BASE_URL}/ledgers/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": "测试台账",
        "description": "这是一个测试台账",
        "template_id": 1,  # 假设模板ID为1
        "data": {"field1": "value1", "field2": "value2"}
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("创建台账成功")
        ledger = response.json()
        print(f"台账ID: {ledger['id']}")
        return ledger["id"]
    else:
        print(f"创建台账失败: {response.status_code}")
        print(response.text)
        return None

# 测试获取工作流列表
def test_get_workflows(token):
    url = f"{BASE_URL}/workflows/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取工作流列表成功")
        workflows = response.json()
        print(f"工作流数量: {len(workflows)}")
        if workflows:
            print("第一个工作流:")
            pprint(workflows[0])
            return workflows[0]["id"]
    else:
        print(f"获取工作流列表失败: {response.status_code}")
        print(response.text)
        return None

# 测试创建工作流
def test_create_workflow(token):
    url = f"{BASE_URL}/workflows/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": "测试工作流",
        "description": "这是一个测试工作流",
        "template_id": 1,  # 假设模板ID为1
        "is_active": True,
        "nodes": [
            {
                "name": "开始节点",
                "description": "工作流开始",
                "node_type": "start",
                "order_index": 0,
                "workflow_id": 0  # 会被后端替换
            },
            {
                "name": "审批节点",
                "description": "主管审批",
                "node_type": "approval",
                "approver_user_id": 1,  # 假设用户ID为1
                "order_index": 1,
                "workflow_id": 0  # 会被后端替换
            },
            {
                "name": "结束节点",
                "description": "工作流结束",
                "node_type": "end",
                "order_index": 2,
                "is_final": True,
                "workflow_id": 0  # 会被后端替换
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("创建工作流成功")
        workflow = response.json()
        print(f"工作流ID: {workflow['id']}")
        return workflow["id"]
    else:
        print(f"创建工作流失败: {response.status_code}")
        print(response.text)
        return None

# 测试提交台账审批
def test_submit_ledger(token, ledger_id, workflow_id):
    url = f"{BASE_URL}/approvals/ledgers/{ledger_id}/submit"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "workflow_id": workflow_id
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("提交台账审批成功")
        ledger = response.json()
        print(f"台账状态: {ledger['status']}")
        print(f"审批状态: {ledger.get('approval_status', 'N/A')}")
        return True
    else:
        print(f"提交台账审批失败: {response.status_code}")
        print(response.text)
        return False

# 测试获取待办任务
def test_get_pending_tasks(token):
    url = f"{BASE_URL}/approvals/tasks"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取待办任务成功")
        tasks = response.json()
        print(f"待办任务数量: {len(tasks)}")
        if tasks:
            print("第一个待办任务:")
            pprint(tasks[0])
            return tasks[0]["ledger_id"] if "ledger_id" in tasks[0] else None
    else:
        print(f"获取待办任务失败: {response.status_code}")
        print(response.text)
        return None

# 测试审批台账
def test_approve_ledger(token, ledger_id):
    url = f"{BASE_URL}/approvals/ledgers/{ledger_id}/approve"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "action": "approve",
        "comment": "同意"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("审批台账成功")
        ledger = response.json()
        print(f"台账状态: {ledger['status']}")
        print(f"审批状态: {ledger.get('approval_status', 'N/A')}")
        return True
    else:
        print(f"审批台账失败: {response.status_code}")
        print(response.text)
        return False

# 测试获取工作流实例
def test_get_workflow_instance(token, instance_id):
    url = f"{BASE_URL}/approvals/workflow-instances/{instance_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取工作流实例成功")
        instance = response.json()
        print(f"工作流实例ID: {instance['id']}")
        if 'nodes' in instance and instance['nodes']:
            print(f"节点数量: {len(instance['nodes'])}")
            print("第一个节点:")
            pprint(instance['nodes'][0])
        return True
    else:
        print(f"获取工作流实例失败: {response.status_code}")
        print(response.text)
        return False

# 测试获取审计日志
def test_get_audit_logs(token, ledger_id):
    url = f"{BASE_URL}/logs/audit?ledger_id={ledger_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取审计日志成功")
        logs = response.json()
        print(f"日志数量: {len(logs)}")
        if logs:
            print("第一条日志:")
            pprint(logs[0])
        return True
    else:
        print(f"获取审计日志失败: {response.status_code}")
        print(response.text)
        return False

# 测试获取系统日志
def test_get_system_logs(token):
    url = f"{BASE_URL}/logs/system"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("获取系统日志成功")
        logs = response.json()
        print(f"日志数量: {len(logs)}")
        if logs:
            print("第一条日志:")
            pprint(logs[0])
        return True
    else:
        print(f"获取系统日志失败: {response.status_code}")
        print(response.text)
        return False

# 主函数
def main():
    print("等待API服务启动...")
    # 尝试连接API服务
    max_attempts = 5
    attempts = 0
    while attempts < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("API服务已启动")
                break
        except Exception as e:
            print(f"尝试连接API服务失败: {e}")
        
        attempts += 1
        print(f"等待5秒后重试... ({attempts}/{max_attempts})")
        time.sleep(5)
    
    if attempts >= max_attempts:
        print("无法连接到API服务，请确保后端服务已启动")
        return
    
    # 获取访问令牌
    token = get_access_token()
    if not token:
        return
    
    success_count = 0
    test_count = 0
    
    print("\n=== 测试获取台账列表 ===")
    test_count += 1
    if test_get_ledgers(token):
        success_count += 1
    
    print("\n=== 测试创建台账 ===")
    test_count += 1
    ledger_id = test_create_ledger(token)
    if ledger_id:
        success_count += 1
    
    print("\n=== 测试获取工作流列表 ===")
    test_count += 1
    workflow_id = test_get_workflows(token)
    if workflow_id:
        success_count += 1
    
    if not workflow_id:
        print("\n=== 测试创建工作流 ===")
        test_count += 1
        workflow_id = test_create_workflow(token)
        if workflow_id:
            success_count += 1
    
    # 测试工作流相关功能
    if ledger_id and workflow_id:
        print("\n=== 测试提交台账审批 ===")
        test_count += 1
        if test_submit_ledger(token, ledger_id, workflow_id):
            success_count += 1
            
            print("\n=== 测试获取待办任务 ===")
            test_count += 1
            task_ledger_id = test_get_pending_tasks(token)
            if task_ledger_id:
                success_count += 1
            
            print("\n=== 测试审批台账 ===")
            test_count += 1
            if test_approve_ledger(token, ledger_id):
                success_count += 1
            
            print("\n=== 测试获取审计日志 ===")
            test_count += 1
            if test_get_audit_logs(token, ledger_id):
                success_count += 1
    
    print("\n=== 测试获取系统日志 ===")
    test_count += 1
    if test_get_system_logs(token):
        success_count += 1
    
    print(f"\n=== 测试完成: {success_count}/{test_count} 测试通过 ===")
    if success_count == test_count:
        print("所有测试通过！")
    else:
        print(f"有 {test_count - success_count} 个测试失败，请检查日志并修复问题。")

if __name__ == "__main__":
    main() 