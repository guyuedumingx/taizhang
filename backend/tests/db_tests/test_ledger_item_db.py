import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app import crud, models, schemas


def test_create_ledger_item(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试创建台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建台账
    ledger_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    # 直接使用模型创建
    import json
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data = jsonable_encoder(ledger_in)
    db_obj = models.Ledger(**obj_in_data)
    db_obj.created_by_id = user.id
    db_obj.updated_by_id = user.id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    ledger = db_obj

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
    
    # 创建台账条目
    item_value = "Test Value"
    ledger_item_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item_value,
    )
    
    ledger_item = crud.ledger_item.create(db, obj_in=ledger_item_in)
    
    assert ledger_item.ledger_id == ledger.id
    assert ledger_item.field_id == field.id
    assert ledger_item.value == item_value


def test_get_ledger_item(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试获取台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建台账
    ledger_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    # 直接使用模型创建
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data = jsonable_encoder(ledger_in)
    db_obj = models.Ledger(**obj_in_data)
    db_obj.created_by_id = user.id
    db_obj.updated_by_id = user.id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    ledger = db_obj

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
    
    # 创建台账条目
    item_value = "Test Value"
    ledger_item_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item_value,
    )
    
    created_ledger_item = crud.ledger_item.create(db, obj_in=ledger_item_in)
    
    fetched_ledger_item = crud.ledger_item.get(db, id=created_ledger_item.id)
    
    assert fetched_ledger_item
    assert fetched_ledger_item.id == created_ledger_item.id
    assert fetched_ledger_item.ledger_id == ledger.id
    assert fetched_ledger_item.field_id == field.id
    assert fetched_ledger_item.value == item_value


def test_update_ledger_item(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试更新台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建台账
    ledger_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    # 直接使用模型创建
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data = jsonable_encoder(ledger_in)
    db_obj = models.Ledger(**obj_in_data)
    db_obj.created_by_id = user.id
    db_obj.updated_by_id = user.id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    ledger = db_obj

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
    
    # 创建台账条目
    item_value = "Test Value"
    ledger_item_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item_value,
    )
    
    created_ledger_item = crud.ledger_item.create(db, obj_in=ledger_item_in)
    
    new_value = "Updated Value"
    
    ledger_item_update = schemas.LedgerItemUpdate(
        value=new_value,
    )
    
    updated_ledger_item = crud.ledger_item.update(db, db_obj=created_ledger_item, obj_in=ledger_item_update)
    
    assert updated_ledger_item.id == created_ledger_item.id
    assert updated_ledger_item.value == new_value
    assert updated_ledger_item.ledger_id == ledger.id  # 未更新的字段应保持不变
    assert updated_ledger_item.field_id == field.id  # 未更新的字段应保持不变


def test_delete_ledger_item(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试删除台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建台账
    ledger_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    # 直接使用模型创建
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data = jsonable_encoder(ledger_in)
    db_obj = models.Ledger(**obj_in_data)
    db_obj.created_by_id = user.id
    db_obj.updated_by_id = user.id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    ledger = db_obj

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
    
    # 创建台账条目
    item_value = "Test Value"
    ledger_item_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item_value,
    )
    
    created_ledger_item = crud.ledger_item.create(db, obj_in=ledger_item_in)
    ledger_item_id = created_ledger_item.id
    
    deleted_ledger_item = crud.ledger_item.remove(db, id=ledger_item_id)
    
    assert deleted_ledger_item.id == ledger_item_id
    
    # 确认台账条目已被删除
    fetched_ledger_item = crud.ledger_item.get(db, id=ledger_item_id)
    assert fetched_ledger_item is None


def test_get_multi_ledger_items(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试获取多个台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建台账
    ledger_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    # 直接使用模型创建
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data = jsonable_encoder(ledger_in)
    db_obj = models.Ledger(**obj_in_data)
    db_obj.created_by_id = user.id
    db_obj.updated_by_id = user.id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    ledger = db_obj

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
    
    # 创建多个台账条目
    item1_value = "Test Value 1"
    item2_value = "Test Value 2"
    
    ledger_item1_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item1_value,
    )
    
    ledger_item2_in = schemas.LedgerItemCreate(
        ledger_id=ledger.id,
        field_id=field.id,
        value=item2_value,
    )
    
    crud.ledger_item.create(db, obj_in=ledger_item1_in)
    crud.ledger_item.create(db, obj_in=ledger_item2_in)
    
    ledger_items = crud.ledger_item.get_multi(db)
    
    assert len(ledger_items) == 2
    assert any(item.value == item1_value for item in ledger_items)
    assert any(item.value == item2_value for item in ledger_items)


def test_get_ledger_items_by_ledger(db: Session, test_template: dict, test_user: dict, test_ledger: dict, test_field: dict):
    """测试通过台账ID获取所有台账条目"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建多个台账
    ledger1_in = schemas.LedgerCreate(
        name=test_ledger["title"],
        template_id=template.id
    )
    
    ledger2_in = schemas.LedgerCreate(
        name=f"{test_ledger['title']}_2",
        template_id=template.id
    )
    
    # 直接使用模型创建第一个台账
    from fastapi.encoders import jsonable_encoder
    
    obj_in_data1 = jsonable_encoder(ledger1_in)
    db_obj1 = models.Ledger(**obj_in_data1)
    db_obj1.created_by_id = user.id
    db_obj1.updated_by_id = user.id
    db.add(db_obj1)
    db.commit()
    db.refresh(db_obj1)
    ledger1 = db_obj1
    
    # 直接使用模型创建第二个台账
    obj_in_data2 = jsonable_encoder(ledger2_in)
    db_obj2 = models.Ledger(**obj_in_data2)
    db_obj2.created_by_id = user.id
    db_obj2.updated_by_id = user.id
    db.add(db_obj2)
    db.commit()
    db.refresh(db_obj2)
    ledger2 = db_obj2

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
    
    # 为第一个台账创建多个条目
    item1_value = "Test Value 1"
    item2_value = "Test Value 2"
    
    ledger_item1_in = schemas.LedgerItemCreate(
        ledger_id=ledger1.id,
        field_id=field.id,
        value=item1_value,
    )
    
    ledger_item2_in = schemas.LedgerItemCreate(
        ledger_id=ledger1.id,
        field_id=field.id,
        value=item2_value,
    )
    
    # 为第二个台账创建条目
    item3_value = "Test Value 3"
    
    ledger_item3_in = schemas.LedgerItemCreate(
        ledger_id=ledger2.id,
        field_id=field.id,
        value=item3_value,
    )
    
    crud.ledger_item.create(db, obj_in=ledger_item1_in)
    crud.ledger_item.create(db, obj_in=ledger_item2_in)
    crud.ledger_item.create(db, obj_in=ledger_item3_in)
    
    # 获取第一个台账的所有条目
    ledger1_items = crud.ledger_item.get_by_ledger(db, ledger_id=ledger1.id)
    
    assert len(ledger1_items) == 2
    assert all(item.ledger_id == ledger1.id for item in ledger1_items)
    
    # 获取第二个台账的所有条目
    ledger2_items = crud.ledger_item.get_by_ledger(db, ledger_id=ledger2.id)
    
    assert len(ledger2_items) == 1
    assert ledger2_items[0].ledger_id == ledger2.id 