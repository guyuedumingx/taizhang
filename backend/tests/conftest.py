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

第四个必须隔离的点 —— casbin（2026-10-21 补）：
  services/casbin_service.get_enforcer() 用 settings.SQLALCHEMY_DATABASE_URI
  **自己 create_engine**, 完全绕开上面三处 SessionLocal 替换, 且 _enforcer
  是模块级单例跨测试复用。后果: 测试用户 id 从 1 起, 与开发库 id 空间撞车 ——
  开发库 casbin_rule 里 'g 1 admin' 使测试里的"第一个用户"(正常是普通员工)
  被判为管理员, 权限类断言假阳性通过 (实测: 普通员工能批量建号 200 而非 403)。
  同时 add_role_for_user 会把测试产生的角色写进开发库。
  修法: 把 enforcer 绑到同一个内存库 engine, 策略复用 init_db.init_permissions()
  (不复制策略字面量, 保证与生产永不漂移), 并在测毕重置单例。
"""
import os

import pytest
from typing import Dict, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token
from app.db import session as session_mod
from app.db.session import Base
from app.portrait import models as _portrait_models  # noqa: F401 触发 portrait ORM 注册
from app.services import casbin_service
from app.utils import logger as logger_mod
from tests.utils.user import create_random_user

# casbin_rule 不是 ORM 模型, Base.metadata 里没有, 须手工建表。
# 列定义对齐 casbin_sqlalchemy_adapter 期望的 id/ptype/v0..v5。
_CASBIN_RULE_DDL = """
CREATE TABLE IF NOT EXISTS casbin_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ptype VARCHAR(100),
    v0 VARCHAR(100), v1 VARCHAR(100), v2 VARCHAR(100),
    v3 VARCHAR(100), v4 VARCHAR(100), v5 VARCHAR(100)
)
"""


def _bind_casbin_to(engine):
    """把 casbin enforcer 绑到给定 engine (替代连开发库的原实现)。"""
    import casbin
    from casbin_sqlalchemy_adapter import Adapter

    model_path = os.path.join(
        os.path.dirname(os.path.dirname(casbin_service.__file__)), "core", "rbac_model.conf"
    )

    def _get_enforcer():
        return casbin.Enforcer(model_path, Adapter(engine))

    casbin_service.get_enforcer = _get_enforcer
    casbin_service._enforcer = None  # 清掉模块级单例, 避免复用上一个已 dispose 的 engine


def _seed_policies():
    """把 init_db 的权威角色策略灌进隔离库 —— 复用生产定义而非复制字面量。"""
    from app.db.init_db import init_permissions

    init_permissions()


@pytest.fixture(scope="function", autouse=True)
def _isolated_db():
    """函数级内存库 + 三点 SessionLocal 替换 + casbin 隔离，测毕还原。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text(_CASBIN_RULE_DDL))

    original_core = session_mod.SessionLocal
    original_deps = deps.SessionLocal
    original_logger = logger_mod.SessionLocal
    original_get_enforcer = casbin_service.get_enforcer
    original_enforcer_singleton = casbin_service._enforcer
    factory = lambda: Session(bind=engine)  # noqa: E731
    session_mod.SessionLocal = factory
    deps.SessionLocal = factory
    logger_mod.SessionLocal = factory
    _bind_casbin_to(engine)
    _seed_policies()
    try:
        yield engine
    finally:
        session_mod.SessionLocal = original_core
        deps.SessionLocal = original_deps
        logger_mod.SessionLocal = original_logger
        casbin_service.get_enforcer = original_get_enforcer
        casbin_service._enforcer = original_enforcer_singleton
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

    同时赋 casbin 角色 —— 与生产 user_service.create_user 一致；
    crud.user.create 不赋角色，隔离后若不补，普通用户将无任何权限。
    """
    user_in = schemas.UserCreate(
        username="admin",
        ehr_id="1000001",
        name="测试管理员",
        password="Admin123!",
        department="测试部门",
        is_superuser=True,
        is_active=True,
    )
    user = crud.user.create(db, obj_in=user_in)
    casbin_service.add_role_for_user(str(user.id), "admin")
    return user


@pytest.fixture(scope="function")
def normal_user(db: Session) -> models.User:
    """
    创建测试普通用户

    赋 'user' 角色（生产默认角色），否则 casbin 侧无任何放行。
    """
    user = create_random_user(db, email="user@example.com", password="User123!")
    casbin_service.add_role_for_user(str(user.id), "user")
    return user


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
