import pytest
from typing import Generator, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app import models


@pytest.fixture(scope="function")
def db() -> Generator:
    """创建一个测试数据库会话，每个测试函数都会重置数据库"""
    # 在每个测试函数前重建数据库
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """返回测试用户数据"""
    return {
        "username": "testuser",
        "ehr_id": "1234567",
        "password": "password123",
        "hashed_password": get_password_hash("password123"),
        "name": "Test User",
        "department": "Test Department",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def test_admin() -> Dict[str, Any]:
    """返回测试管理员用户数据"""
    return {
        "username": "testadmin",
        "ehr_id": "7654321",
        "password": "admin123",
        "hashed_password": get_password_hash("admin123"),
        "name": "Test Admin",
        "department": "Admin Department",
        "is_active": True,
        "is_superuser": True,
    }


@pytest.fixture
def test_team() -> Dict[str, Any]:
    """返回测试团队数据"""
    return {
        "name": "Test Team",
        "department": "Test Department",
        "description": "This is a test team",
    }


@pytest.fixture
def test_role() -> Dict[str, Any]:
    """返回测试角色数据"""
    return {
        "name": "test_role",
        "description": "Test Role Description",
        "is_system": False,
    }


@pytest.fixture
def test_template() -> Dict[str, Any]:
    """返回测试模板数据"""
    return {
        "name": "Test Template",
        "description": "This is a test template",
        "is_system": False,
    }


@pytest.fixture
def test_field() -> Dict[str, Any]:
    """返回测试字段数据"""
    return {
        "name": "test_field",
        "label": "测试字段",
        "field_type": "text",  # 用于创建时
        "type": "text",  # 对应数据库中的字段类型
        "description": "Test Field Description",
        "required": True,
        "options": None,
        "default_value": "",
        "order": 0,
        "is_key_field": True
    }


@pytest.fixture
def test_workflow() -> Dict[str, Any]:
    """返回测试工作流数据"""
    return {
        "name": "Test Workflow",
        "description": "This is a test workflow",
        "is_active": True,
    }


@pytest.fixture
def test_ledger() -> Dict[str, Any]:
    """返回测试台账数据"""
    return {
        "name": "Test Ledger",
        "status": "draft",
        "description": "Test Ledger Description",
        "created_at": datetime.now(),
        "modified_at": datetime.now(),
    }


@pytest.fixture
def test_system_log() -> Dict[str, Any]:
    """返回测试系统日志数据"""
    return {
        "level": "info",
        "message": "Test log message",
        "resource_type": "user",
        "resource_id": "1",
        "action": "create",
        "timestamp": datetime.now(),
    }


@pytest.fixture
def test_audit_log() -> Dict[str, Any]:
    """返回测试审计日志数据"""
    return {
        "user_id": 1,
        "resource_type": "ledger",
        "resource_id": "1",
        "action": "create",
        "description": "Created test ledger",
        "timestamp": datetime.now(),
    } 