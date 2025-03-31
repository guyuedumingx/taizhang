import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_workflow_node(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试获取工作流节点"""
    # 先创建一个测试节点
    node_in = schemas.WorkflowNodeCreate(
        name="测试获取节点",
        description="用于测试获取的节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node = crud.workflow_node.create(db, obj_in=node_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/workflow-nodes/{node.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == node.id
    assert data["name"] == node.name
    assert data["description"] == node.description
    assert data["node_type"] == node.node_type
    assert data["workflow_id"] == workflow.id
    
    # 清理测试数据
    db.delete(node)
    db.commit()


def test_create_workflow_node(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试创建工作流节点"""
    node_data = {
        "name": "测试API创建节点",
        "description": "通过API创建的测试节点",
        "node_type": "approval",
        "order_index": 1,
        "workflow_id": workflow.id,
        "is_final": False
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-nodes/",
        headers=admin_token_headers,
        json=node_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == node_data["name"]
    assert data["description"] == node_data["description"]
    assert data["node_type"] == node_data["node_type"]
    assert data["workflow_id"] == workflow.id
    
    # 清理测试数据
    node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == data["id"]).first()
    if node:
        db.delete(node)
        db.commit()


def test_update_workflow_node(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试更新工作流节点"""
    # 先创建一个测试节点
    node_in = schemas.WorkflowNodeCreate(
        name="待更新的节点",
        description="将被更新的节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node = crud.workflow_node.create(db, obj_in=node_in)
    
    update_data = {
        "name": "已更新的节点名称",
        "description": "已更新的节点描述",
        "is_final": True
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/workflow-nodes/{node.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == node.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["is_final"] == update_data["is_final"]
    assert data["workflow_id"] == workflow.id
    
    # 清理测试数据
    db.delete(node)
    db.commit()


def test_delete_workflow_node(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试删除工作流节点"""
    # 先创建一个测试节点
    node_in = schemas.WorkflowNodeCreate(
        name="待删除的节点",
        description="将被删除的节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node = crud.workflow_node.create(db, obj_in=node_in)
    
    response = client.delete(
        f"{settings.API_V1_STR}/workflow-nodes/{node.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证节点已被删除
    deleted_node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node.id).first()
    assert deleted_node is None


def test_get_workflow_nodes_by_workflow(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试获取工作流所有节点"""
    # 先创建几个测试节点
    node1_in = schemas.WorkflowNodeCreate(
        name="测试节点1",
        description="第一个测试节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node1 = crud.workflow_node.create(db, obj_in=node1_in)
    
    node2_in = schemas.WorkflowNodeCreate(
        name="测试节点2",
        description="第二个测试节点",
        node_type="approval",
        order_index=2,
        workflow_id=workflow.id
    )
    node2 = crud.workflow_node.create(db, obj_in=node2_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/workflow-nodes/workflow/{workflow.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any(n["id"] == node1.id for n in data)
    assert any(n["id"] == node2.id for n in data)
    
    # 清理测试数据
    db.delete(node1)
    db.delete(node2)
    db.commit()


def test_update_workflow_node_order(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试更新工作流节点顺序"""
    # 先创建几个测试节点
    node1_in = schemas.WorkflowNodeCreate(
        name="顺序节点1",
        description="第一个顺序节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node1 = crud.workflow_node.create(db, obj_in=node1_in)
    
    node2_in = schemas.WorkflowNodeCreate(
        name="顺序节点2",
        description="第二个顺序节点",
        node_type="approval",
        order_index=2,
        workflow_id=workflow.id
    )
    node2 = crud.workflow_node.create(db, obj_in=node2_in)
    
    # 更新顺序
    order_data = {
        "node_orders": [
            {"id": node1.id, "order_index": 2},
            {"id": node2.id, "order_index": 1}
        ]
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-nodes/orders",
        headers=admin_token_headers,
        json=order_data,
    )
    
    assert response.status_code == 200
    
    # 验证顺序已更新
    updated_node1 = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node1.id).first()
    updated_node2 = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node2.id).first()
    assert updated_node1.order_index == 2
    assert updated_node2.order_index == 1
    
    # 清理测试数据
    db.delete(node1)
    db.delete(node2)
    db.commit()


def test_add_workflow_node_approver(db: Session, admin_token_headers: dict, workflow: models.Workflow, normal_user: models.User):
    """测试添加工作流节点审批人"""
    # 先创建一个测试节点
    node_in = schemas.WorkflowNodeCreate(
        name="测试审批人节点",
        description="用于测试添加审批人的节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node = crud.workflow_node.create(db, obj_in=node_in)
    
    # 添加审批人
    approver_data = {
        "user_id": normal_user.id
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflow-nodes/{node.id}/approvers",
        headers=admin_token_headers,
        json=approver_data,
    )
    
    assert response.status_code == 200
    
    # 验证审批人已添加
    node_with_approvers = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node.id).first()
    assert len(node_with_approvers.approvers) == 1
    assert node_with_approvers.approvers[0].id == normal_user.id
    
    # 清理测试数据
    # 先移除节点与审批人的关系
    node_with_approvers.approvers = []
    db.add(node_with_approvers)
    db.commit()
    # 然后删除节点
    db.delete(node)
    db.commit()
