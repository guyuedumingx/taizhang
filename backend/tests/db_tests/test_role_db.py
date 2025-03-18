import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas


def test_create_role(db: Session, test_role: dict):
    """测试创建角色"""
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    assert role.name == test_role["name"]
    assert role.description == test_role["description"]
    assert role.is_system == test_role["is_system"]


def test_get_role(db: Session, test_role: dict):
    """测试获取角色"""
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    created_role = crud.role.create(db, obj_in=role_in)
    
    fetched_role = crud.role.get(db, id=created_role.id)
    
    assert fetched_role
    assert fetched_role.id == created_role.id
    assert fetched_role.name == test_role["name"]
    assert fetched_role.description == test_role["description"]


def test_get_role_by_name(db: Session, test_role: dict):
    """测试通过名称获取角色"""
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    crud.role.create(db, obj_in=role_in)
    
    fetched_role = crud.role.get_by_name(db, name=test_role["name"])
    
    assert fetched_role
    assert fetched_role.name == test_role["name"]
    assert fetched_role.description == test_role["description"]


def test_update_role(db: Session, test_role: dict):
    """测试更新角色"""
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    created_role = crud.role.create(db, obj_in=role_in)
    
    new_description = "Updated Role Description"
    
    role_update = schemas.RoleUpdate(
        description=new_description,
    )
    
    updated_role = crud.role.update(db, db_obj=created_role, obj_in=role_update)
    
    assert updated_role.id == created_role.id
    assert updated_role.description == new_description
    assert updated_role.name == test_role["name"]  # 没有更新的字段应保持不变


def test_delete_role(db: Session, test_role: dict):
    """测试删除角色"""
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    created_role = crud.role.create(db, obj_in=role_in)
    role_id = created_role.id
    
    deleted_role = crud.role.remove(db, id=role_id)
    
    assert deleted_role.id == role_id
    
    # 确认角色已被删除
    fetched_role = crud.role.get(db, id=role_id)
    assert fetched_role is None


def test_get_multi_roles(db: Session, test_role: dict):
    """测试获取多个角色"""
    # 创建第一个角色
    role1_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    # 创建第二个角色
    role2_in = schemas.RoleCreate(
        name=f"{test_role['name']}_2",
        description=f"{test_role['description']} 2",
        is_system=False,
    )
    
    crud.role.create(db, obj_in=role1_in)
    crud.role.create(db, obj_in=role2_in)
    
    roles = crud.role.get_multi(db)
    
    assert len(roles) == 2
    assert any(r.name == test_role["name"] for r in roles)
    assert any(r.name == f"{test_role['name']}_2" for r in roles) 