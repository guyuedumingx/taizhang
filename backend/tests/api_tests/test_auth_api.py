import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_login_access_token(normal_user_dict: dict):
    """测试用户登录获取访问令牌"""
    login_data = {
        "username": normal_user_dict["email"],
        "password": normal_user_dict["password"],
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/access-token",
        data=login_data,  # 注意：登录接口使用表单数据，不是JSON
    )
    
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_with_wrong_password(normal_user_dict: dict):
    """测试使用错误密码登录"""
    login_data = {
        "username": normal_user_dict["email"],
        "password": "wrong_password",
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/access-token",
        data=login_data,
    )
    
    assert response.status_code == 400
    assert "detail" in response.json()


def test_login_with_nonexistent_user():
    """测试使用不存在的用户登录"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "password123",
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/access-token",
        data=login_data,
    )
    
    assert response.status_code == 400
    assert "detail" in response.json()


def test_use_access_token(normal_token_headers: dict, normal_user: models.User):
    """测试使用访问令牌获取当前用户信息"""
    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_token_headers,
    )
    
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == normal_user.email
    assert user_data["id"] == normal_user.id


def test_register_user(db: Session):
    """测试用户注册"""
    # 注册新用户数据
    user_data = {
        "email": "test_register@example.com",
        "password": "StrongPassword123!",
        "name": "测试注册用户",
        "phone": "13800138999",
        "department": "测试部门",
        "position": "测试职位"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=user_data,
    )
    
    # 验证响应
    assert response.status_code == 200
    created_user = response.json()
    assert created_user["email"] == user_data["email"]
    assert created_user["name"] == user_data["name"]
    assert "password" not in created_user  # 确保密码不在响应中
    
    # 清理测试数据
    user = db.query(models.User).filter(models.User.email == user_data["email"]).first()
    if user:
        db.delete(user)
        db.commit()


def test_register_existing_user(normal_user: models.User):
    """测试注册已存在的用户"""
    user_data = {
        "email": normal_user.email,  # 使用已存在用户的邮箱
        "password": "StrongPassword123!",
        "name": "测试重复注册",
        "phone": "13800138777",
        "department": "测试部门",
        "position": "测试职位"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=user_data,
    )
    
    # 验证响应状态码（应该是400或409）
    assert response.status_code >= 400
    assert "detail" in response.json()
