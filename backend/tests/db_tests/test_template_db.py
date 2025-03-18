import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas


def test_create_template(db: Session, test_template: dict):
    """测试创建模板"""
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    assert template.name == test_template["name"]
    assert template.description == test_template["description"]
    assert template.is_system == test_template["is_system"]
    assert template.department == "测试部门"


def test_get_template(db: Session, test_template: dict):
    """测试获取模板"""
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    created_template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    fetched_template = crud.template.get(db, id=created_template.id)
    
    assert fetched_template
    assert fetched_template.id == created_template.id
    assert fetched_template.name == test_template["name"]
    assert fetched_template.description == test_template["description"]
    assert fetched_template.is_system == test_template["is_system"]
    assert fetched_template.department == "测试部门"


def test_update_template(db: Session, test_template: dict):
    """测试更新模板"""
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )

    created_template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    new_description = "Updated Template Description"
    template_update = schemas.TemplateUpdate(description=new_description)
    updated_template = crud.template.update(db, db_obj=created_template, obj_in=template_update, updater_id=1)
    
    assert updated_template.id == created_template.id
    assert updated_template.name == created_template.name
    assert updated_template.description == new_description
    assert updated_template.is_system == created_template.is_system
    assert updated_template.department == created_template.department


def test_delete_template(db: Session, test_template: dict):
    """测试删除模板"""
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )

    created_template = crud.template.create(db, obj_in=template_in, creator_id=1)
    template_id = created_template.id
    
    crud.template.remove(db, id=template_id)
    deleted_template = crud.template.get(db, id=template_id)
    assert deleted_template is None


def test_get_multi_templates(db: Session, test_template: dict):
    """测试获取多个模板"""
    # 创建第一个模板
    template1_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    # 创建第二个模板
    template2_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=False,
        department="测试部门2",
        fields=[]
    )
    
    crud.template.create(db, obj_in=template1_in, creator_id=1)
    crud.template.create(db, obj_in=template2_in, creator_id=1)
    
    templates = crud.template.get_multi(db, skip=0, limit=10)
    
    assert len(templates) >= 2
    assert any(t.name == template1_in.name for t in templates)
    assert any(t.name == template2_in.name for t in templates)


def test_template_with_fields(db: Session, test_template: dict, test_field: dict):
    """测试模板及其字段关系"""
    # 创建字段
    field_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        description=test_field["description"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    # 创建模板并包含字段
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[field_in]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 获取模板的字段
    fields = crud.field.get_by_template(db, template_id=template.id)
    
    assert len(fields) == 1
    assert fields[0].name == test_field["name"]
    assert fields[0].type == test_field["field_type"]
    assert fields[0].required == test_field["required"]
    assert fields[0].is_key_field == test_field["is_key_field"] 