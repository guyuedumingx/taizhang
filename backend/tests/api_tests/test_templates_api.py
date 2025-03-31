import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_templates(db: Session, normal_token_headers: dict, template: models.Template):
    """测试获取模板列表"""
    response = client.get(
        f"{settings.API_V1_STR}/templates/",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 确认创建的测试模板在列表中
    assert any(t["id"] == template.id for t in data)


def test_create_template(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试创建模板"""
    template_data = {
        "name": "测试API创建模板",
        "description": "通过API测试创建的模板",
        "department": "财务部",
        "workflow_id": workflow.id,
        "fields": [
            {
                "name": "字段1",
                "field_type": "text",
                "label": "测试字段1",
                "placeholder": "请输入文本",
                "required": True,
                "order": 1
            },
            {
                "name": "字段2",
                "field_type": "number",
                "label": "测试字段2",
                "placeholder": "请输入数字",
                "required": False,
                "order": 2
            }
        ]
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/templates/",
        headers=admin_token_headers,
        json=template_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == template_data["name"]
    assert data["description"] == template_data["description"]
    assert data["department"] == template_data["department"]
    assert data["workflow_id"] == workflow.id
    assert len(data["fields"]) == 2
    
    # 清理测试数据
    created_template = db.query(models.Template).filter(models.Template.name == template_data["name"]).first()
    if created_template:
        # 先删除关联的字段
        db.query(models.Field).filter(models.Field.template_id == created_template.id).delete()
        db.delete(created_template)
        db.commit()


def test_get_template(db: Session, normal_token_headers: dict, template: models.Template):
    """测试获取单个模板详情"""
    response = client.get(
        f"{settings.API_V1_STR}/templates/{template.id}",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template.id
    assert data["name"] == template.name
    assert data["description"] == template.description
    assert "fields" in data


def test_update_template(db: Session, admin_token_headers: dict, template: models.Template):
    """测试更新模板信息"""
    update_data = {
        "name": "已更新的模板名称",
        "description": "已更新的模板描述",
        "department": "已更新的部门"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/templates/{template.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["department"] == update_data["department"]


def test_delete_template(db: Session, admin_token_headers: dict, workflow: models.Workflow):
    """测试删除模板"""
    # 创建一个待删除的模板
    template_data = {
        "name": "待删除的测试模板",
        "description": "将被删除的测试模板",
        "department": "测试部门",
        "workflow_id": workflow.id,
        "fields": []
    }
    
    # 创建模板
    response = client.post(
        f"{settings.API_V1_STR}/templates/",
        headers=admin_token_headers,
        json=template_data,
    )
    assert response.status_code == 200
    template_id = response.json()["id"]
    
    # 删除模板
    response = client.delete(
        f"{settings.API_V1_STR}/templates/{template_id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证模板已被删除
    response = client.get(
        f"{settings.API_V1_STR}/templates/{template_id}",
        headers=normal_token_headers,
    )
    assert response.status_code == 404


def test_get_template_fields(db: Session, normal_token_headers: dict, template: models.Template):
    """测试获取模板字段列表"""
    response = client.get(
        f"{settings.API_V1_STR}/templates/{template.id}/fields",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 字段可能为空，无法确定具体数量


def test_add_template_field(db: Session, admin_token_headers: dict, template: models.Template):
    """测试添加模板字段"""
    field_data = {
        "name": "new_field",
        "field_type": "text",
        "label": "新字段",
        "placeholder": "请输入",
        "required": True,
        "order": 1
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/templates/{template.id}/fields",
        headers=admin_token_headers,
        json=field_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == field_data["name"]
    assert data["field_type"] == field_data["field_type"]
    assert data["label"] == field_data["label"]
    assert data["template_id"] == template.id
    
    # 清理测试数据
    field = db.query(models.Field).filter(
        models.Field.template_id == template.id,
        models.Field.name == field_data["name"]
    ).first()
    if field:
        db.delete(field)
        db.commit()


def test_update_template_field(db: Session, admin_token_headers: dict, template: models.Template):
    """测试更新模板字段"""
    # 先创建一个字段
    field_in = schemas.FieldCreate(
        name="test_update_field",
        field_type="text",
        label="待更新的字段",
        placeholder="请输入",
        required=True,
        order=1
    )
    field = crud.field.create(db, obj_in=field_in, template_id=template.id)
    
    # 更新字段
    update_data = {
        "label": "已更新的字段标签",
        "placeholder": "已更新的placeholder",
        "required": False
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/templates/{template.id}/fields/{field.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == field.id
    assert data["template_id"] == template.id
    assert data["label"] == update_data["label"]
    assert data["placeholder"] == update_data["placeholder"]
    assert data["required"] == update_data["required"]
    
    # 清理测试数据
    db.delete(field)
    db.commit()


def test_delete_template_field(db: Session, admin_token_headers: dict, template: models.Template):
    """测试删除模板字段"""
    # 先创建一个字段
    field_in = schemas.FieldCreate(
        name="test_delete_field",
        field_type="text",
        label="待删除的字段",
        placeholder="请输入",
        required=True,
        order=1
    )
    field = crud.field.create(db, obj_in=field_in, template_id=template.id)
    
    # 删除字段
    response = client.delete(
        f"{settings.API_V1_STR}/templates/{template.id}/fields/{field.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证字段已被删除
    deleted_field = db.query(models.Field).filter(models.Field.id == field.id).first()
    assert deleted_field is None
