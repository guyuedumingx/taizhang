import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_workflows(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试获取工作流列表"""
    response = client.get(
        f"{settings.API_V1_STR}/workflows/",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # 测试搜索功能
    response = client.get(
        f"{settings.API_V1_STR}/workflows/?search={workflow.name}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(w["name"] == workflow.name for w in data)


def test_create_workflow(db: Session, normal_token_headers: dict):
    """测试创建工作流"""
    workflow_data = {
        "name": "API测试工作流",
        "description": "通过API创建的工作流",
        "nodes": [
            {
                "name": "节点1",
                "description": "第一个节点",
                "node_type": "approval",
                "order_index": 1
            },
            {
                "name": "节点2",
                "description": "第二个节点",
                "node_type": "approval",
                "order_index": 2,
                "reject_to_node_id": None
            }
        ]
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflows/",
        headers=normal_token_headers,
        json=workflow_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == workflow_data["name"]
    assert data["description"] == workflow_data["description"]
    
    # 清理测试数据
    workflow = db.query(models.Workflow).filter(models.Workflow.name == workflow_data["name"]).first()
    if workflow:
        # 先删除关联的节点
        db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).delete()
        db.delete(workflow)
        db.commit()


def test_get_workflow(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试获取单个工作流"""
    response = client.get(
        f"{settings.API_V1_STR}/workflows/{workflow.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow.id
    assert data["name"] == workflow.name
    assert data["description"] == workflow.description
    assert "nodes" in data


def test_update_workflow(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试更新工作流"""
    update_data = {
        "name": "已更新的API工作流",
        "description": "通过API更新的工作流描述"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/workflows/{workflow.id}",
        headers=normal_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


def test_delete_workflow(db: Session, normal_token_headers: dict):
    """测试删除工作流"""
    # 创建测试工作流
    workflow_data = {
        "name": "待删除的API工作流",
        "description": "将被删除的工作流"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/workflows/",
        headers=normal_token_headers,
        json=workflow_data,
    )
    
    assert response.status_code == 200
    workflow_id = response.json()["id"]
    
    # 删除工作流
    response = client.delete(
        f"{settings.API_V1_STR}/workflows/{workflow_id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证工作流已被删除
    response = client.get(
        f"{settings.API_V1_STR}/workflows/{workflow_id}",
        headers=normal_token_headers,
    )
    assert response.status_code == 404  # 工作流应该不存在了


def test_get_workflow_nodes(db: Session, normal_token_headers: dict, workflow: models.Workflow):
    """测试获取工作流节点"""
    response = client.get(
        f"{settings.API_V1_STR}/workflows/{workflow.id}/nodes",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(node["workflow_id"] == workflow.id for node in data)
