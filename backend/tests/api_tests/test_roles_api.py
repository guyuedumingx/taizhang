import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_create_role(db: Session, admin_token_headers: dict):
    """测试创建角色"""
    random_suffix = uuid.uuid4().hex[:8]
    role_data = {
        "name": f"测试角色_{random_suffix}",
        "description": "用于测试的角色",
        "permissions": ["read_users", "write_ledgers"]
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=admin_token_headers,
        json=role_data,
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == role_data["name"]
    assert data["description"] == role_data["description"]
    assert "permissions" in data
    
    # 清理测试数据
    role = db.query(models.Role).filter(models.Role.name == role_data["name"]).first()
    if role:
        db.delete(role)
        db.commit()


def test_get_roles(db: Session, admin_token_headers: dict):
    """测试获取角色列表"""
    # 先创建测试角色
    random_suffix = uuid.uuid4().hex[:8]
    test_role = crud.role.create(
        db=db,
        obj_in=schemas.RoleCreate(
            name=f"测试角色列表_{random_suffix}",
            description="用于测试角色列表的角色",
            permissions=["read_users"]
        )
    )
    
    response = client.get(
        f"{settings.API_V1_STR}/roles/",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 检查创建的测试角色是否在列表中
    role_exists = any(role["id"] == test_role.id for role in data)
    assert role_exists is True
    
    # 清理测试数据
    db.delete(test_role)
    db.commit()


def test_get_role(db: Session, admin_token_headers: dict):
    """测试获取单个角色"""
    # 先创建测试角色
    random_suffix = uuid.uuid4().hex[:8]
    test_role = crud.role.create(
        db=db,
        obj_in=schemas.RoleCreate(
            name=f"测试获取角色_{random_suffix}",
            description="用于测试获取单个角色的角色",
            permissions=["read_users", "read_ledgers"]
        )
    )
    
    response = client.get(
        f"{settings.API_V1_STR}/roles/{test_role.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_role.id
    assert data["name"] == test_role.name
    assert data["description"] == test_role.description
    assert "permissions" in data
    
    # 清理测试数据
    db.delete(test_role)
    db.commit()


def test_update_role(db: Session, admin_token_headers: dict):
    """测试更新角色"""
    # 先创建测试角色
    random_suffix = uuid.uuid4().hex[:8]
    update_suffix = uuid.uuid4().hex[:8]
    test_role = crud.role.create(
        db=db,
        obj_in=schemas.RoleCreate(
            name=f"测试更新角色_{random_suffix}",
            description="用于测试更新的角色",
            permissions=["read_users"]
        )
    )
    
    update_data = {
        "name": f"已更新的角色_{update_suffix}",
        "description": "已更新的描述",
        "permissions": ["read_users", "write_users"]
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/roles/{test_role.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_role.id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert "permissions" in data
    
    # 清理测试数据
    db.delete(test_role)
    db.commit()


def test_delete_role(db: Session, admin_token_headers: dict):
    """测试删除角色"""
    # 先创建测试角色
    random_suffix = uuid.uuid4().hex[:8]
    test_role = crud.role.create(
        db=db,
        obj_in=schemas.RoleCreate(
            name=f"测试删除角色_{random_suffix}",
            description="用于测试删除的角色",
            permissions=["read_users"]
        )
    )
    
    role_id = test_role.id
    
    response = client.delete(
        f"{settings.API_V1_STR}/roles/{role_id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    
    # 验证角色已被删除
    deleted_role = db.query(models.Role).filter(models.Role.id == role_id).first()
    assert deleted_role is None
