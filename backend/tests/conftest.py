import pytest
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal, engine, Base
from app.api.deps import get_db, get_current_active_user
from app import models


@pytest.fixture(scope="session")
def db() -> Generator:
    Base.metadata.drop_all(bind=engine)  # 清除数据
    Base.metadata.create_all(bind=engine)  # 创建表
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_user() -> models.User:
    """返回一个管理员用户对象"""
    return models.User(
        id=1,
        username="testadmin",
        ehr_id="1234567",
        name="Test Admin",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 密码: admin123
        is_active=True,
        is_superuser=True
    )


@pytest.fixture(scope="module")
def normal_user() -> models.User:
    """返回一个普通用户对象"""
    return models.User(
        id=2,
        username="normaluser",
        ehr_id="7654321",
        name="Normal User",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 密码: admin123
        is_active=True,
        is_superuser=False
    )


@pytest.fixture(scope="module")
def admin_token(admin_user) -> str:
    """生成管理员用户的访问令牌"""
    from app.core.security import create_access_token
    return create_access_token({"sub": admin_user.username})


@pytest.fixture(scope="module")
def normal_token(normal_user) -> str:
    """生成普通用户的访问令牌"""
    from app.core.security import create_access_token
    return create_access_token({"sub": normal_user.username})


@pytest.fixture(scope="function")
def use_admin_user(admin_user):
    """使用管理员用户覆盖当前用户依赖"""
    original = getattr(app.dependency_overrides, get_current_active_user, None)
    
    def get_test_admin():
        return admin_user
    
    app.dependency_overrides[get_current_active_user] = get_test_admin
    
    yield admin_user
    
    if original:
        app.dependency_overrides[get_current_active_user] = original
    else:
        del app.dependency_overrides[get_current_active_user]


@pytest.fixture(scope="function")
def use_normal_user(normal_user):
    """使用普通用户覆盖当前用户依赖"""
    original = getattr(app.dependency_overrides, get_current_active_user, None)
    
    def get_test_normal_user():
        return normal_user
    
    app.dependency_overrides[get_current_active_user] = get_test_normal_user
    
    yield normal_user
    
    if original:
        app.dependency_overrides[get_current_active_user] = original
    else:
        del app.dependency_overrides[get_current_active_user] 