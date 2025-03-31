import string
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import random
from app import crud, models, schemas
from app.core.config import settings
from app.main import app
from tests.utils.user import create_random_user
from tests.utils.utils import random_email, random_lower_string

client = TestClient(app)

def test_login_access_token(db: Session):
    """测试用户登录获取访问令牌"""
    password = random_lower_string()
    username = random_lower_string(8)
    ehr_id = f"{100_0000 + abs(hash(username)) % 900_0000}"[-7:]
    
    # 创建一个测试用户
    user_in = schemas.UserCreate(
        username=username,
        ehr_id=ehr_id,
        name=f"测试用户_{username[:5]}",
        password=password,
        department="测试部门"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    # 测试使用EHR ID登录
    login_data = {
        "username": ehr_id,  # 使用EHR ID作为用户名
        "password": password,
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/login", data=login_data
    )
    tokens = response.json()
    
    assert response.status_code == 200
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"
    
    # 清理测试数据
    db.delete(user)
    db.commit()


def test_login_access_token_with_wrong_password(db: Session):
    """测试用户使用错误密码登录"""
    password = random_lower_string()
    username = random_lower_string(8)
    ehr_id = f"{100_0000 + abs(hash(username)) % 900_0000}"[-7:]
    
    # 创建一个测试用户
    user_in = schemas.UserCreate(
        username=username,
        ehr_id=ehr_id,
        name=f"测试用户_{username[:5]}",
        password=password,
        department="测试部门"
    )
    user = crud.user.create(db, obj_in=user_in)
    
    # 测试使用错误密码登录
    login_data = {
        "username": ehr_id,  # 使用EHR ID作为用户名
        "password": password + "wrong",
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/login", data=login_data
    )
    
    assert response.status_code in [400, 401]  # 接受400或401
    assert "detail" in response.json()
    
    # 清理测试数据
    db.delete(user)
    db.commit()


def test_user_me(db: Session, normal_token_headers: dict):
    """测试获取当前登录用户信息"""
    response = client.get(
        f"{settings.API_V1_STR}/auth/me", headers=normal_token_headers
    )
    
    assert response.status_code == 200
    user_data = response.json()
    assert "id" in user_data
    assert "username" in user_data
    assert "is_active" in user_data
    assert user_data["is_active"] is True
