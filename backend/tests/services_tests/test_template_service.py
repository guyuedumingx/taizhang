import pytest
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.template.template_service import template_service


def test_get_templates(db: Session, normal_user: models.User):
    """测试获取模板列表"""
    # 创建测试数据
    template_in = schemas.TemplateCreate(
        name="测试模板1",
        description="这是测试模板1",
        department="测试部门"
    )
    template_service.create_template(db, template_in, normal_user.id)
    
    template_in2 = schemas.TemplateCreate(
        name="测试模板2",
        description="这是测试模板2",
        department="测试部门2"
    )
    template_service.create_template(db, template_in2, normal_user.id)
    
    # 测试获取全部模板
    templates = template_service.get_templates(db)
    assert len(templates) == 2
    assert templates[0].name == "测试模板1"
    assert templates[1].name == "测试模板2"
    
    # 测试搜索功能
    templates = template_service.get_templates(db, search="测试模板1")
    assert len(templates) == 1
    assert templates[0].name == "测试模板1"
    
    # 测试分页功能
    templates = template_service.get_templates(db, skip=1, limit=1)
    assert len(templates) == 1
    assert templates[0].name == "测试模板2"


def test_create_template(db: Session, normal_user: models.User):
    """测试创建模板"""
    # 创建测试数据
    template_in = schemas.TemplateCreate(
        name="新模板",
        description="这是一个新模板",
        department="新部门",
        fields=[
            schemas.FieldCreate(
                name="字段1",
                label="测试字段1",
                type="text",
                required=True,
                order=1
            ),
            schemas.FieldCreate(
                name="字段2",
                label="测试字段2",
                type="number",
                required=False,
                order=2
            )
        ]
    )
    
    # 创建模板
    template = template_service.create_template(db, template_in, normal_user.id)
    
    # 验证创建结果
    assert template.name == "新模板"
    assert template.description == "这是一个新模板"
    assert template.department == "新部门"
    assert template.created_by_id == normal_user.id
    assert template.updated_by_id == normal_user.id
    assert template.field_count == 2
    
    # 测试重复名称
    with pytest.raises(Exception):
        template_service.create_template(db, template_in, normal_user.id)


def test_get_template(db: Session, normal_user: models.User):
    """测试获取单个模板"""
    # 创建测试数据
    template_in = schemas.TemplateCreate(
        name="测试模板",
        description="这是一个测试模板",
        department="测试部门",
        fields=[
            schemas.FieldCreate(
                name="字段1",
                label="测试字段1",
                type="text",
                required=True,
                order=1
            )
        ]
    )
    created_template = template_service.create_template(db, template_in, normal_user.id)
    
    # 获取模板
    template = template_service.get_template(db, created_template.id)
    
    # 验证结果
    assert template.id == created_template.id
    assert template.name == "测试模板"
    assert template.description == "这是一个测试模板"
    assert template.department == "测试部门"
    assert len(template.fields) == 1
    assert template.fields[0].name == "字段1"
    
    # 测试不存在的模板
    with pytest.raises(Exception):
        template_service.get_template(db, 999)


def test_update_template(db: Session, normal_user: models.User):
    """测试更新模板"""
    # 创建测试数据
    template_in = schemas.TemplateCreate(
        name="原模板",
        description="原描述",
        department="原部门",
        fields=[
            schemas.FieldCreate(
                name="原字段",
                label="原标签",
                type="text",
                required=True,
                order=1
            )
        ]
    )
    template = template_service.create_template(db, template_in, normal_user.id)
    
    # 更新数据
    update_data = schemas.TemplateUpdate(
        name="更新后的模板",
        description="更新后的描述",
        department="更新后的部门"
    )
    
    # 更新模板
    updated_template = template_service.update_template(db, template.id, update_data, normal_user.id)
    
    # 验证更新结果
    assert updated_template.name == "更新后的模板"
    assert updated_template.description == "更新后的描述"
    assert updated_template.department == "更新后的部门"
    
    # 测试不存在的模板
    with pytest.raises(Exception):
        template_service.update_template(db, 999, update_data, normal_user.id)


def test_delete_template(db: Session, normal_user: models.User):
    """测试删除模板"""
    # 创建测试数据
    template_in = schemas.TemplateCreate(
        name="待删除模板",
        description="这是待删除的模板",
        department="测试部门"
    )
    template = template_service.create_template(db, template_in, normal_user.id)
    
    # 删除模板
    deleted_template = template_service.delete_template(db, template.id)
    
    # 验证删除结果
    assert deleted_template.id == template.id
    assert deleted_template.name == "待删除模板"
    
    # 确认模板已被删除
    with pytest.raises(Exception):
        template_service.get_template(db, template.id)
    
    # 测试删除不存在的模板
    with pytest.raises(Exception):
        template_service.delete_template(db, 999) 