import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import random

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
    # 检查分页响应格式
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data
    assert "page" in data
    assert "size" in data


def test_create_user(db: Session, admin_token_headers: dict):
    """测试创建新用户"""
    # 生成随机用户名和EHR ID
    random_suffix = uuid.uuid4().hex[:8]
    random_ehr = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    
    user_data = {
        "username": f"test_create_api_{random_suffix}",
        "ehr_id": random_ehr,  # 随机生成7位数字
        "password": "Password123!",
        "name": "测试创建用户",
        "department": "测试部门",
        "is_active": True
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=admin_token_headers,
        json=user_data,
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content}")
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["ehr_id"] == user_data["ehr_id"]
    assert data["name"] == user_data["name"]
    assert data["department"] == user_data["department"]
    assert "id" in data
    
    # 清理测试数据
    user = db.query(models.User).filter(models.User.username == user_data["username"]).first()
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
    assert data["username"] == normal_user.username
    assert data["name"] == normal_user.name


def test_update_user(db: Session, admin_token_headers: dict):
    """测试更新用户"""
    # 创建测试用户
    user_in = schemas.UserCreate(
        username="test_update_api",
        ehr_id="7654321",  # 需要7位数字
        password="Password123!",
        name="更新前的用户",
        department="测试部门"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    update_data = {
        "name": "更新后的用户",
        "department": "更新后的部门"
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
    
    # 清理测试数据
    db.delete(user)
    db.commit()


def test_update_user_me(db: Session, normal_token_headers: dict, normal_user: models.User):
    """测试用户更新自己的信息"""
    update_data = {
        "name": "自我更新的用户名",
        "department": "自我更新的部门"
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/users/{normal_user.id}",
        headers=normal_token_headers,
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["department"] == update_data["department"]
    assert data["id"] == normal_user.id


def test_get_user_me(normal_token_headers: dict, normal_user: models.User):
    """测试获取当前用户信息"""
    response = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == normal_user.id
    assert data["username"] == normal_user.username
    assert data["name"] == normal_user.name


def test_delete_user(db: Session, admin_token_headers: dict):
    """测试删除用户"""
    # 创建测试用户
    user_in = schemas.UserCreate(
        username="test_delete_api",
        ehr_id="7891234",  # 需要7位数字
        password="Password123!",
        name="待删除的用户",
        department="测试部门"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    user_id = user.id
    
    response = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 204
    
    # 验证用户已被删除
    deleted_user = db.query(models.User).filter(models.User.id == user_id).first()
    assert deleted_user is None
