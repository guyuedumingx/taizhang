import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_users(db: Session, admin_token_headers: dict):
    """测试获取用户列表"""
    response = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_create_user(db: Session, admin_token_headers: dict):
    """测试创建新用户"""
    user_data = {
        "email": "test_create_api@example.com",
        "password": "Password123!",
        "name": "测试创建用户",
        "phone": "13800138000",
        "department": "测试部门",
        "position": "测试职位",
        "is_active": True
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=admin_token_headers,
        json=user_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["phone"] == user_data["phone"]
    assert data["department"] == user_data["department"]
    assert data["position"] == user_data["position"]
    assert data["is_active"] == user_data["is_active"]
    assert "password" not in data  # 确保密码未在响应中返回
    
    # 清理测试数据
    user = db.query(models.User).filter(models.User.email == user_data["email"]).first()
    if user:
        db.delete(user)
        db.commit()


def test_get_user(db: Session, admin_token_headers: dict, normal_user: models.User):
    """测试获取单个用户"""
    response = client.get(
        f"{settings.API_V1_STR}/users/{normal_user.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == normal_user.id
    assert data["email"] == normal_user.email
    assert data["name"] == normal_user.name


def test_update_user(db: Session, admin_token_headers: dict):
    """测试更新用户"""
    # 创建测试用户
    user_in = schemas.UserCreate(
        email="test_update_api@example.com",
        password="Password123!",
        name="更新前的用户",
        phone="13800138001",
        department="测试部门",
        position="测试职位"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    update_data = {
        "name": "更新后的用户",
        "department": "更新后的部门",
        "position": "更新后的职位"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=admin_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["name"] == update_data["name"]
    assert data["department"] == update_data["department"]
    assert data["position"] == update_data["position"]
    
    # 清理测试数据
    db.delete(user)
    db.commit()


def test_update_user_me(db: Session, normal_token_headers: dict, normal_user: models.User):
    """测试用户更新自己的信息"""
    update_data = {
        "name": "自我更新的用户名",
        "phone": "13900139000"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["phone"] == update_data["phone"]
    assert data["id"] == normal_user.id


def test_get_user_me(normal_token_headers: dict, normal_user: models.User):
    """测试获取当前用户信息"""
    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == normal_user.id
    assert data["email"] == normal_user.email
    assert data["name"] == normal_user.name


def test_delete_user(db: Session, admin_token_headers: dict):
    """测试删除用户"""
    # 创建测试用户
    user_in = schemas.UserCreate(
        email="test_delete_api@example.com",
        password="Password123!",
        name="待删除的用户",
        phone="13800138002",
        department="测试部门",
        position="测试职位"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    user_id = user.id
    
    response = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    
    # 验证用户已被删除
    deleted_user = db.query(models.User).filter(models.User.id == user_id).first()
    assert deleted_user is None
