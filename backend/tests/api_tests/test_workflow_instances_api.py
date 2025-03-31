import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_workflow_instance(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试获取工作流实例"""
    response = client.get(
        f"{settings.API_V1_STR}/workflow-instances/{workflow_instance.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow_instance.id
    assert data["workflow_id"] == workflow_instance.workflow_id
    assert data["ledger_id"] == workflow_instance.ledger_id
    assert data["status"] == workflow_instance.status
    assert "nodes" in data


def test_get_workflow_instances(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试获取工作流实例列表"""
    response = client.get(
        f"{settings.API_V1_STR}/workflow-instances/",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 确认测试工作流实例在列表中
    assert any(wi["id"] == workflow_instance.id for wi in data)


def test_get_workflow_instance_nodes(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试获取工作流实例节点"""
    response = client.get(
        f"{settings.API_V1_STR}/workflow-instances/{workflow_instance.id}/nodes",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(node["workflow_instance_id"] == workflow_instance.id for node in data)


def test_create_workflow_instance(db: Session, admin_token_headers: dict, workflow: models.Workflow, ledger: models.Ledger):
    """测试创建工作流实例"""
    # 确保没有已存在的工作流实例关联到该台账
    existing_instance = db.query(models.WorkflowInstance).filter(models.WorkflowInstance.ledger_id == ledger.id).first()
    if existing_instance:
        # 移除关联节点
        db.query(models.WorkflowInstanceNode).filter(models.WorkflowInstanceNode.workflow_instance_id == existing_instance.id).delete()
        # 移除实例
        db.delete(existing_instance)
        db.commit()
    
    instance_data = {
        "workflow_id": workflow.id,
        "ledger_id": ledger.id,
        "status": "active"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-instances/",
        headers=admin_token_headers,
        json=instance_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow.id
    assert data["ledger_id"] == ledger.id
    assert data["status"] == "active"
    assert "nodes" in data and len(data["nodes"]) > 0
    
    # 清理测试数据
    instance = db.query(models.WorkflowInstance).filter(models.WorkflowInstance.id == data["id"]).first()
    if instance:
        # 先删除关联的节点
        db.query(models.WorkflowInstanceNode).filter(models.WorkflowInstanceNode.workflow_instance_id == instance.id).delete()
        # 再删除实例
        db.delete(instance)
        db.commit()


def test_update_workflow_instance(db: Session, admin_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试更新工作流实例"""
    update_data = {
        "status": "completed",
        "completed_at": "2023-04-01T12:00:00"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/workflow-instances/{workflow_instance.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow_instance.id
    assert data["status"] == update_data["status"]
    assert "completed_at" in data and data["completed_at"] is not None


def test_approve_workflow_instance_node(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试审批工作流实例节点"""
    # 获取当前待审批的节点
    current_node = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.workflow_instance_id == workflow_instance.id,
        models.WorkflowInstanceNode.status == "pending"
    ).first()
    
    if not current_node:
        pytest.skip("没有待审批的节点，跳过测试")
    
    # 设置当前审批人
    current_node.approver_id = 1  # 假设测试用户ID为1
    db.add(current_node)
    db.commit()
    
    # 审批数据
    approval_data = {
        "action": "approve",
        "comment": "测试审批通过"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-instances/{workflow_instance.id}/nodes/{current_node.id}/approve",
        headers=normal_token_headers,
        json=approval_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert "approver_actions" in data and len(data["approver_actions"]) > 0
    assert data["approver_actions"][0]["action"] == "approve"


def test_reject_workflow_instance_node(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance):
    """测试拒绝工作流实例节点"""
    # 创建一个新的待审批节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=1  # 假设测试用户ID为1
    )
    db.add(instance_node)
    db.commit()
    db.refresh(instance_node)
    
    # 拒绝数据
    rejection_data = {
        "action": "reject",
        "comment": "测试拒绝理由"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-instances/{workflow_instance.id}/nodes/{instance_node.id}/reject",
        headers=normal_token_headers,
        json=rejection_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert "approver_actions" in data and len(data["approver_actions"]) > 0
    assert data["approver_actions"][0]["action"] == "reject"
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()


def test_get_my_pending_approvals(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance, normal_user: models.User):
    """测试获取我的待审批列表"""
    # 创建一个待审批节点并指定当前用户为审批人
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    
    response = client.get(
        f"{settings.API_V1_STR}/workflow-instances/my-pending-approvals",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(approval["id"] == instance_node.id for approval in data)
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()


def test_get_my_workflow_instances(db: Session, normal_token_headers: dict, workflow_instance: models.WorkflowInstance, normal_user: models.User):
    """测试获取我创建的工作流实例"""
    # 确保该实例是由测试用户创建的
    workflow_instance.created_by = normal_user.id
    db.add(workflow_instance)
    db.commit()
    
    response = client.get(
        f"{settings.API_V1_STR}/workflow-instances/my-instances",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(wi["id"] == workflow_instance.id for wi in data)
