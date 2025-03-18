import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app import models, schemas
from app.services.user.user_service import UserService as user_service
from app.core.security import verify_password


def test_get_users(db: Session, superuser: models.User, normal_user: models.User):
    """测试获取用户列表"""
    users = user_service.get_users(db)
    assert len(users) >= 2
    assert any(user.id == superuser.id for user in users)
    assert any(user.id == normal_user.id for user in users)


def test_create_user(db: Session):
    """测试创建用户"""
    # 创建测试数据
    user_in = schemas.UserCreate(
        username="testuser",
        ehr_id="1234567",  # 确保是7位数字
        password="password123",
        name="测试用户",
        department="测试部门",
        team_id=None,
        roles=["user"]
    )
    
    # 创建用户
    user = user_service.create_user(db, user_in)
    
    # 验证创建结果
    assert user.username == "testuser"
    assert user.ehr_id == "1234567"
    assert user.name == "测试用户"
    assert user.department == "测试部门"
    assert user.is_active is True
    assert user.is_superuser is False
    assert verify_password("password123", user.hashed_password)
    assert "user" in user.roles
    
    # 测试重复创建
    with pytest.raises(HTTPException) as excinfo:
        user_service.create_user(db, user_in)
    assert excinfo.value.status_code == 400


def test_get_user(db: Session, normal_user: models.User):
    """测试获取单个用户"""
    # 获取用户
    user = user_service.get_user(db, normal_user.id)
    
    # 验证结果
    assert user.id == normal_user.id
    assert user.username == normal_user.username
    assert user.name == normal_user.name
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        user_service.get_user(db, 999)


def test_update_user(db: Session, normal_user: models.User):
    """测试更新用户"""
    # 更新数据
    update_data = schemas.UserUpdate(
        name="更新的名字",
        department="更新的部门",
    )
    
    # 更新用户
    updated_user = user_service.update_user(db, normal_user.id, update_data)
    
    # 验证更新结果
    assert updated_user.id == normal_user.id
    assert updated_user.name == "更新的名字"
    assert updated_user.department == "更新的部门"
    
    # 测试更新密码
    update_data = schemas.UserUpdate(
        password="newpassword123"
    )
    updated_user = user_service.update_user(db, normal_user.id, update_data)
    assert verify_password("newpassword123", updated_user.hashed_password)
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        user_service.update_user(db, 999, update_data)


def test_delete_user(db: Session):
    """测试删除用户"""
    # 创建测试用户
    user_in = schemas.UserCreate(
        username="deleteuser",
        ehr_id="7654321",  # 确保是7位数字
        password="password123",
        name="待删除用户",
        department="测试部门",
        roles=["user"]  # 添加 roles 属性
    )
    user = user_service.create_user(db, user_in)
    
    # 删除用户
    deleted_user = user_service.delete_user(db, user.id)
    
    # 验证删除结果
    assert deleted_user.id == user.id
    assert deleted_user.username == "deleteuser"
    
    # 确认用户已被删除
    with pytest.raises(Exception):
        user_service.get_user(db, user.id)
    
    # 测试删除不存在的用户
    with pytest.raises(Exception):
        user_service.delete_user(db, 999)


def test_check_password_expired(db: Session, normal_user: models.User):
    """测试检查密码是否过期"""
    # 检查密码过期状态
    result = user_service.check_password_expired(normal_user)
    
    # 验证结果包含正确的键
    assert "password_expired" in result
    assert "days_until_expiry" in result
    assert "last_password_change" in result 