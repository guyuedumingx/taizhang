import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_ledgers(db: Session, normal_token_headers: dict, ledger: models.Ledger):
    """测试获取台账列表"""
    response = client.get(
        f"{settings.API_V1_STR}/ledgers/",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 确认创建的测试台账在列表中
    assert any(l["id"] == ledger.id for l in data)


def test_create_ledger(db: Session, normal_token_headers: dict, template: models.Template, team: models.Team):
    """测试创建台账"""
    ledger_data = {
        "name": "测试API创建台账",
        "description": "通过API测试创建的台账",
        "team_id": team.id,
        "template_id": template.id,
        "data": {
            "field1": "值1",
            "field2": 123
        }
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/",
        headers=normal_token_headers,
        json=ledger_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == ledger_data["name"]
    assert data["description"] == ledger_data["description"]
    assert data["team_id"] == team.id
    assert data["template_id"] == template.id
    assert data["status"] == "draft"  # 默认状态为草稿
    
    # 清理测试数据
    ledger = db.query(models.Ledger).filter(models.Ledger.name == ledger_data["name"]).first()
    if ledger:
        # 删除关联的字段值
        db.query(models.FieldValue).filter(models.FieldValue.ledger_id == ledger.id).delete()
        # 删除台账
        db.delete(ledger)
        db.commit()


def test_get_ledger(db: Session, normal_token_headers: dict, ledger: models.Ledger):
    """测试获取单个台账详情"""
    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ledger.id
    assert data["name"] == ledger.name
    assert data["description"] == ledger.description
    assert "field_values" in data
    assert "template" in data


def test_update_ledger(db: Session, normal_token_headers: dict, ledger: models.Ledger):
    """测试更新台账信息"""
    update_data = {
        "name": "已更新的台账名称",
        "description": "已更新的台账描述",
        "data": {
            "field1": "更新后的值1",
            "field2": 456
        }
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}",
        headers=normal_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ledger.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


def test_delete_ledger(db: Session, normal_token_headers: dict, template: models.Template, team: models.Team):
    """测试删除台账"""
    # 创建一个待删除的台账
    ledger_data = {
        "name": "待删除的测试台账",
        "description": "将被删除的测试台账",
        "team_id": team.id,
        "template_id": template.id
    }
    
    # 创建台账
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/",
        headers=normal_token_headers,
        json=ledger_data,
    )
    assert response.status_code == 200
    ledger_id = response.json()["id"]
    
    # 删除台账
    response = client.delete(
        f"{settings.API_V1_STR}/ledgers/{ledger_id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证台账已被删除
    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger_id}",
        headers=normal_token_headers,
    )
    assert response.status_code == 404


def test_submit_ledger(db: Session, normal_token_headers: dict, ledger: models.Ledger, workflow: models.Workflow):
    """测试提交台账"""
    # 确保台账关联了工作流程
    db_ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger.id).first()
    # 获取模板
    template = db_ledger.template
    # 更新模板关联的工作流程
    template.workflow_id = workflow.id
    db.add(template)
    db.commit()
    
    # 提交数据
    submit_data = {
        "workflow_id": workflow.id,
        "comment": "测试提交台账到审批流程"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/submit",
        headers=normal_token_headers,
        json=submit_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ledger.id
    assert data["status"] == "active"  # 提交后状态应为active
    assert data["approval_status"] == "pending"  # 审批状态为pending
    assert "submitted_at" in data and data["submitted_at"] is not None
    assert "workflow_instance" in data


def test_get_ledger_field_values(db: Session, normal_token_headers: dict, ledger: models.Ledger):
    """测试获取台账字段值"""
    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/field-values",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_ledger_field_value(db: Session, normal_token_headers: dict, ledger: models.Ledger, template: models.Template):
    """测试更新台账字段值"""
    # 创建一个字段
    field_in = schemas.FieldCreate(
        name="test_field",
        field_type="text",
        label="测试字段",
        placeholder="请输入",
        required=True,
        order=1
    )
    field = crud.field.create(db, obj_in=field_in, template_id=template.id)
    
    # 创建一个字段值
    field_value_in = schemas.FieldValueCreate(
        field_id=field.id,
        value="初始值"
    )
    field_value = crud.field_value.create(db, obj_in=field_value_in, ledger_id=ledger.id)
    
    # 更新字段值
    update_data = {
        "value": "更新后的值"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/field-values/{field_value.id}",
        headers=normal_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == field_value.id
    assert data["ledger_id"] == ledger.id
    assert data["field_id"] == field.id
    assert data["value"] == update_data["value"]
    
    # 清理测试数据
    db.delete(field_value)
    db.delete(field)
    db.commit()


def test_search_ledgers(db: Session, normal_token_headers: dict, ledger: models.Ledger):
    """测试搜索台账"""
    response = client.get(
        f"{settings.API_V1_STR}/ledgers/search?keyword={ledger.name}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(l["id"] == ledger.id for l in data)
