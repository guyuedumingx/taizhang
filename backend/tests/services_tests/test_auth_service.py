import pytest
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException

from app import crud, models, schemas
from app.services.auth_service import AuthService as auth_service
from app.core.security import verify_password

# 测试用户登录
def test_authenticate_user(db: Session, normal_user: models.User):
    """测试用户登录"""
    # 验证正确的凭据
    token = auth_service.authenticate_user(db, ehr_id=normal_user.ehr_id, password="password123")
    
    # 验证结果
    assert token
    assert "access_token" in token
    assert token["user_id"] == normal_user.id
    assert token["username"] == normal_user.username
    
    # 测试错误的密码
    with pytest.raises(HTTPException) as excinfo:
        auth_service.authenticate_user(db, ehr_id=normal_user.ehr_id, password="wrong_password")
    assert excinfo.value.status_code == 401
    
    # 测试不存在的用户
    with pytest.raises(HTTPException) as excinfo:
        auth_service.authenticate_user(db, ehr_id="9999999", password="password123")
    assert excinfo.value.status_code == 401

# 测试用户注册
def test_register_user(db: Session):
    """测试用户注册"""
    # 注册数据
    user_in = schemas.UserCreate(
        username="registeruser",
        ehr_id="1234567",  # 7位数字
        password="password123",
        name="注册用户",
        department="测试部门"
    )
    
    # 注册用户
    user = auth_service.register_user(db, user_in)
    
    # 验证结果
    assert user
    assert user.username == "registeruser"
    assert user.ehr_id == "1234567"
    assert user.name == "注册用户"
    
    # 测试重复注册
    with pytest.raises(HTTPException) as excinfo:
        auth_service.register_user(db, user_in)
    assert excinfo.value.status_code == 400

# 测试修改密码
def test_change_password(db: Session, normal_user: models.User):
    """测试修改密码"""
    # 修改密码数据
    password_data = schemas.PasswordChange(
        current_password="password123",
        new_password="newpassword123"
    )
    
    # 修改密码
    result = auth_service.change_password(db, normal_user.id, password_data)
    
    # 验证结果
    assert "message" in result
    assert result["message"] == "密码修改成功"
    
    # 刷新用户数据
    db.refresh(normal_user)
    assert verify_password("newpassword123", normal_user.hashed_password)
    
    # 测试错误的旧密码
    password_data.current_password = "wrongpassword"
    password_data.new_password = "anotherpassword"
    
    with pytest.raises(HTTPException) as excinfo:
        auth_service.change_password(db, normal_user.id, password_data)
    assert excinfo.value.status_code == 400
    
    # 测试不存在的用户
    with pytest.raises(HTTPException) as excinfo:
        auth_service.change_password(db, 999, password_data)
    assert excinfo.value.status_code == 404