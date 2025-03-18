import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas


def test_create_field(db: Session, test_template: dict, test_field: dict):
    """测试创建字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建字段
    field_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    field = crud.field.create(db, obj_in=field_in.dict() | {"template_id": template.id})
    
    assert field.name == test_field["name"]
    assert field.type == test_field["field_type"]
    assert field.required == test_field["required"]
    assert field.is_key_field == test_field["is_key_field"]
    assert field.template_id == template.id


def test_get_field(db: Session, test_template: dict, test_field: dict):
    """测试获取字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建字段
    field_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    created_field = crud.field.create(db, obj_in=field_in.dict() | {"template_id": template.id})
    
    fetched_field = crud.field.get(db, id=created_field.id)
    
    assert fetched_field
    assert fetched_field.id == created_field.id
    assert fetched_field.name == test_field["name"]
    assert fetched_field.type == test_field["field_type"]
    assert fetched_field.template_id == template.id


def test_update_field(db: Session, test_template: dict, test_field: dict):
    """测试更新字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建字段
    field_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    created_field = crud.field.create(db, obj_in=field_in.dict() | {"template_id": template.id})
    
    # 更新字段
    field_update = schemas.FieldUpdate(
        required=not test_field["required"],
        default_value="新默认值"
    )
    
    updated_field = crud.field.update(db, db_obj=created_field, obj_in=field_update)
    
    assert updated_field.id == created_field.id
    assert updated_field.name == created_field.name
    assert updated_field.type == created_field.type
    assert updated_field.required == (not test_field["required"])
    assert updated_field.default_value == "新默认值"
    assert updated_field.template_id == template.id


def test_delete_field(db: Session, test_template: dict, test_field: dict):
    """测试删除字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建字段
    field_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    created_field = crud.field.create(db, obj_in=field_in.dict() | {"template_id": template.id})
    field_id = created_field.id
    
    crud.field.remove(db, id=field_id)
    deleted_field = crud.field.get(db, id=field_id)
    assert deleted_field is None


def test_get_multi_fields(db: Session, test_template: dict, test_field: dict):
    """测试获取多个字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建第一个字段
    field1_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    # 创建第二个字段
    field2_in = schemas.FieldCreate(
        name=f"{test_field['name']}_2",
        type=test_field["field_type"],
        required=not test_field["required"],
        is_key_field=not test_field["is_key_field"],
        default_value="另一个默认值",
        options=test_field["options"],
    )
    
    crud.field.create(db, obj_in=field1_in.dict() | {"template_id": template.id})
    crud.field.create(db, obj_in=field2_in.dict() | {"template_id": template.id})
    
    fields = crud.field.get_multi(db, skip=0, limit=10)
    
    assert len(fields) >= 2
    assert any(f.name == test_field["name"] for f in fields)
    assert any(f.name == f"{test_field['name']}_2" for f in fields)


def test_get_fields_by_template(db: Session, test_template: dict, test_field: dict):
    """测试获取模板的所有字段"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建同一模板下的两个字段
    field1_in = schemas.FieldCreate(
        name=test_field["name"],
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    field2_in = schemas.FieldCreate(
        name=f"{test_field['name']}_2",
        type=test_field["field_type"],
        required=not test_field["required"],
        is_key_field=not test_field["is_key_field"],
        default_value="另一个默认值",
        options=test_field["options"],
    )
    
    crud.field.create(db, obj_in=field1_in.dict() | {"template_id": template.id})
    crud.field.create(db, obj_in=field2_in.dict() | {"template_id": template.id})
    
    # 创建另一个模板和字段
    another_template_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=test_template["is_system"],
        department="另一个测试部门",
        fields=[]
    )
    
    another_template = crud.template.create(db, obj_in=another_template_in, creator_id=1)
    
    another_field_in = schemas.FieldCreate(
        name=f"{test_field['name']}_3",
        type=test_field["field_type"],
        required=test_field["required"],
        is_key_field=test_field["is_key_field"],
        default_value=test_field["default_value"],
        options=test_field["options"],
    )
    
    crud.field.create(db, obj_in=another_field_in.dict() | {"template_id": another_template.id})
    
    # 获取第一个模板的字段
    template_fields = crud.field.get_by_template(db, template_id=template.id)
    
    assert len(template_fields) == 2
    assert any(f.name == test_field["name"] for f in template_fields)
    assert any(f.name == f"{test_field['name']}_2" for f in template_fields)
    assert all(f.template_id == template.id for f in template_fields) 