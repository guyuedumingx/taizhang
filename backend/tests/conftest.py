"""
pytest 根 conftest —— 全量测试隔离（重构方案 Phase 1.1）

历史问题（审计报告 §6.6）：本文件原先直接用 SessionLocal 连开发库 taizhang.db，
每次跑测试都会往开发库写数据、失败时残留累积（曾积 74 条家访 + 8 条演练残留），
且 8/10 画像测试文件的 TestClient 请求同样打到开发库。

现改为函数级内存库：每个测试用例拿到一个全新空库（全量建表），
断言可以依赖全库基数，且不存在跨用例/跨文件污染。

实现要点（沿用 test_home_visit_f11_f12.py 验证过的模式，推广到全局）：
  - 内存库必须 StaticPool，否则每次新连接拿到一个全新的空库；
  - 必须同时替换三个模块里的 SessionLocal 名字（都是 from-import 按值绑定）：
      app.db.session.SessionLocal —— 真实 get_db 函数体里的那个
      app.api.deps.SessionLocal   —— deps.py 又 import 的一份
      app.utils.logger.SessionLocal —— log_info/log_audit 模块级函数各自开库写日志
    只用 app.dependency_overrides[deps.get_db] 实测改不掉 get_current_user
    子依赖里的那次调用，会出现 current_user 与 router db 身份对不上的问题。
"""
import pytest
from typing import Dict, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token
from app.db import session as session_mod
from app.db.session import Base
from app.portrait import models as _portrait_models  # noqa: F401 触发 portrait ORM 注册
from app.utils import logger as logger_mod
from tests.utils.user import create_random_user


@pytest.fixture(scope="function", autouse=True)
def _isolated_db():
    """函数级内存库 + 三点 SessionLocal 替换，测毕还原。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    original_core = session_mod.SessionLocal
    original_deps = deps.SessionLocal
    original_logger = logger_mod.SessionLocal
    factory = lambda: Session(bind=engine)  # noqa: E731
    session_mod.SessionLocal = factory
    deps.SessionLocal = factory
    logger_mod.SessionLocal = factory
    try:
        yield engine
    finally:
        session_mod.SessionLocal = original_core
        deps.SessionLocal = original_deps
        logger_mod.SessionLocal = original_logger
        engine.dispose()


@pytest.fixture(scope="function")
def db(_isolated_db) -> Generator:
    """数据库会话固件（隔离内存库）"""
    db = Session(bind=_isolated_db)
    try:
        yield db
        db.rollback()
    finally:
        db.close()


@pytest.fixture(scope="function")
def admin_user(db: Session) -> models.User:
    """
    创建测试管理员用户（每个用例的隔离库都是空的，必然新建）
    """
    user_in = schemas.UserCreate(
        username="admin",
        ehr_id="1000001",
        name="测试管理员",
        password="admin123",
        department="测试部门",
        is_superuser=True,
        is_active=True,
    )
    return crud.user.create(db, obj_in=user_in)


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
