import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_pending_approvals(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试获取待审批列表"""
    # 创建一个待审批的实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    
    response = client.get(
        f"{settings.API_V1_STR}/approvals/pending",
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


def test_get_processed_approvals(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试获取已处理的审批列表"""
    # 创建一个已审批的实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="approved",
        approver_id=normal_user.id,
        approver_actions=[{
            "user_id": normal_user.id,
            "user_name": normal_user.name,
            "action": "approve",
            "comment": "测试审批通过",
            "timestamp": "2023-04-01T12:00:00"
        }]
    )
    db.add(instance_node)
    db.commit()
    
    response = client.get(
        f"{settings.API_V1_STR}/approvals/processed",
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


def test_approve(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试审批通过"""
    # 创建一个待审批的实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    db.refresh(instance_node)
    
    approval_data = {
        "comment": "审批通过测试",
        "next_approver_id": None
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/approvals/{instance_node.id}/approve",
        headers=normal_token_headers,
        json=approval_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == instance_node.id
    assert data["status"] == "approved"
    assert "approver_actions" in data
    assert len(data["approver_actions"]) > 0
    assert data["approver_actions"][0]["action"] == "approve"
    assert data["approver_actions"][0]["comment"] == approval_data["comment"]
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()


def test_reject(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试审批拒绝"""
    # 创建一个待审批的实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    db.refresh(instance_node)
    
    rejection_data = {
        "comment": "审批拒绝测试"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/approvals/{instance_node.id}/reject",
        headers=normal_token_headers,
        json=rejection_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == instance_node.id
    assert data["status"] == "rejected"
    assert "approver_actions" in data
    assert len(data["approver_actions"]) > 0
    assert data["approver_actions"][0]["action"] == "reject"
    assert data["approver_actions"][0]["comment"] == rejection_data["comment"]
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()


def test_get_approval_detail(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试获取审批详情"""
    # 创建一个实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    db.refresh(instance_node)
    
    response = client.get(
        f"{settings.API_V1_STR}/approvals/{instance_node.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == instance_node.id
    assert data["workflow_instance_id"] == workflow_instance.id
    assert data["workflow_node_id"] == workflow_node.id
    assert data["status"] == "pending"
    assert data["approver_id"] == normal_user.id
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()


def test_add_comment(db: Session, normal_token_headers: dict, normal_user: models.User, workflow_instance: models.WorkflowInstance):
    """测试添加审批评论"""
    # 创建一个实例节点
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.workflow_id == workflow_instance.workflow_id
    ).first()
    
    if not workflow_node:
        pytest.skip("没有可用的工作流节点，跳过测试")
    
    instance_node = models.WorkflowInstanceNode(
        workflow_instance_id=workflow_instance.id,
        workflow_node_id=workflow_node.id,
        status="pending",
        approver_id=normal_user.id
    )
    db.add(instance_node)
    db.commit()
    db.refresh(instance_node)
    
    comment_data = {
        "comment": "这是一条测试评论"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/approvals/{instance_node.id}/comment",
        headers=normal_token_headers,
        json=comment_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == instance_node.id
    assert "approver_actions" in data
    assert len(data["approver_actions"]) > 0
    assert data["approver_actions"][0]["action"] == "comment"
    assert data["approver_actions"][0]["comment"] == comment_data["comment"]
    
    # 清理测试数据
    db.delete(instance_node)
    db.commit()
