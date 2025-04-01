import pytest
from typing import Dict, Generator
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.db.session import SessionLocal
from app.core.security import create_access_token
from tests.utils.user import create_random_user


@pytest.fixture(scope="session")
def db() -> Generator:
    """数据库会话固件"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def admin_user(db: Session) -> models.User:
    """
    创建测试管理员用户
    """
    # 先尝试获取已存在的管理员
    admin = db.query(models.User).filter(models.User.is_superuser == True).first()
    if admin:
        return admin
    
    # 管理员数据
    user_in = schemas.UserCreate(
        username="admin",
        ehr_id="1000001",
        name="测试管理员",
        password="admin123",
        department="测试部门",
        is_superuser=True,
        is_active=True
    )
    user = crud.user.create(db, obj_in=user_in)
    return user


@pytest.fixture(scope="function")
def normal_user(db: Session) -> models.User:
    """
    创建测试普通用户
    """
    return create_random_user(db, email="user@example.com", password="user123")


@pytest.fixture(scope="function")
def admin_token_headers(admin_user: models.User) -> Dict[str, str]:
    """管理员令牌头"""
    access_token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def normal_token_headers(normal_user: models.User) -> Dict[str, str]:
    """普通用户令牌头"""
    access_token = create_access_token({"sub": str(normal_user.id)})
    return {"Authorization": f"Bearer {access_token}"} 