import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app import crud, models, schemas


def test_create_ledger(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试创建台账"""
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
        name=test_ledger["name"],
        template_id=template.id,
    )
    
    ledger = crud.ledger.create(db, obj_in=ledger_in, created_by_id=user.id, updated_by_id=user.id)
    
    assert ledger.name == test_ledger["name"]
    assert ledger.template_id == template.id
    assert ledger.created_by_id == user.id


def test_get_ledger(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试获取台账"""
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
        name=test_ledger["name"],
        description=test_ledger["description"],
        template_id=template.id,
    )
    
    created_ledger = crud.ledger.create(db, obj_in=ledger_in, created_by_id=user.id, updated_by_id=user.id)
    
    fetched_ledger = crud.ledger.get(db, id=created_ledger.id)
    
    assert fetched_ledger
    assert fetched_ledger.id == created_ledger.id
    assert fetched_ledger.name == test_ledger["name"]
    assert fetched_ledger.template_id == template.id
    assert fetched_ledger.created_by_id == user.id


def test_update_ledger(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试更新台账"""
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
        name=test_ledger["name"],
        description=test_ledger["description"],
        template_id=template.id,
    )
    
    created_ledger = crud.ledger.create(db, obj_in=ledger_in, created_by_id=user.id, updated_by_id=user.id)
    
    new_name = "Updated Ledger Title"
    
    ledger_update = schemas.LedgerUpdate(
        name=new_name,
    )
    
    updated_ledger = crud.ledger.update(db, db_obj=created_ledger, obj_in=ledger_update, updated_by_id=user.id)
    
    assert updated_ledger.id == created_ledger.id
    assert updated_ledger.name == new_name
    assert updated_ledger.template_id == template.id  # 没有更新的字段应保持不变
    assert updated_ledger.description == test_ledger["description"]


def test_delete_ledger(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试删除台账"""
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
        name=test_ledger["name"],
        description=test_ledger["description"],
        template_id=template.id,
    )
    
    created_ledger = crud.ledger.create(db, obj_in=ledger_in, created_by_id=user.id, updated_by_id=user.id)
    ledger_id = created_ledger.id
    
    deleted_ledger = crud.ledger.remove(db, id=ledger_id)
    
    assert deleted_ledger.id == ledger_id
    
    # 确认台账已被删除
    fetched_ledger = crud.ledger.get(db, id=ledger_id)
    assert fetched_ledger is None


def test_get_multi_ledgers(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试获取多个台账"""
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
    
    # 创建第一个台账
    ledger1_in = schemas.LedgerCreate(
        name=test_ledger["name"],
        description=test_ledger["description"],
        template_id=template.id,
    )
    
    # 创建第二个台账
    ledger2_in = schemas.LedgerCreate(
        name=f"{test_ledger['name']}_2",
        description=f"{test_ledger['description']} 2",
        template_id=template.id,
    )
    
    crud.ledger.create(db, obj_in=ledger1_in, created_by_id=user.id, updated_by_id=user.id)
    crud.ledger.create(db, obj_in=ledger2_in, created_by_id=user.id, updated_by_id=user.id)
    
    ledgers = crud.ledger.get_multi(db)
    
    assert len(ledgers) == 2
    assert any(l.name == test_ledger["name"] for l in ledgers)
    assert any(l.name == f"{test_ledger['name']}_2" for l in ledgers)


def test_get_ledgers_by_template(db: Session, test_template: dict, test_user: dict, test_ledger: dict):
    """测试获取模板的所有台账"""
    # 创建两个模板
    template1_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    
    template2_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=False,
        department="测试部门2",
        fields=[]
    )
    
    template1 = crud.template.create(db, obj_in=template1_in, creator_id=1)
    template2 = crud.template.create(db, obj_in=template2_in, creator_id=1)
    
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
    
    # 创建第一个模板的台账
    ledger1_in = schemas.LedgerCreate(
        name=test_ledger["name"],
        template_id=template1.id,
    )
    
    # 创建第二个模板的台账
    ledger2_in = schemas.LedgerCreate(
        name=f"{test_ledger['name']}_2",
        template_id=template2.id,
    )
    
    # 创建另一个第一个模板的台账
    ledger3_in = schemas.LedgerCreate(
        name=f"{test_ledger['name']}_3",
        template_id=template1.id,
    )
    
    crud.ledger.create(db, obj_in=ledger1_in, created_by_id=user.id, updated_by_id=user.id)
    crud.ledger.create(db, obj_in=ledger2_in, created_by_id=user.id, updated_by_id=user.id)
    crud.ledger.create(db, obj_in=ledger3_in, created_by_id=user.id, updated_by_id=user.id)
    
    # 获取第一个模板的所有台账
    template1_ledgers = crud.ledger.get_by_template(db, template_id=template1.id)
    
    assert len(template1_ledgers) == 2
    assert all(l.template_id == template1.id for l in template1_ledgers)
    
    # 获取第二个模板的所有台账
    template2_ledgers = crud.ledger.get_by_template(db, template_id=template2.id)
    
    assert len(template2_ledgers) == 1
    assert template2_ledgers[0].template_id == template2.id 