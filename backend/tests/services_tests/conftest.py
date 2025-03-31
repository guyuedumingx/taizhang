import os
import pytest
from typing import Dict, Generator, List

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app import crud, models, schemas
from app.core.config import settings

# 创建测试数据库引擎
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_services.db"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """
    提供测试数据库会话
    """
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 提供测试会话
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # 清理数据库
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator:
    """
    提供测试客户端
    """
    # 使用测试数据库会话替代默认会话
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # 清理
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def superuser(db: Session) -> models.User:
    """
    创建测试超级用户
    """
    # 超级用户数据
    user_in = schemas.UserCreate(
        name="超级管理员",
        username="admin",
        password="password123",
        is_superuser=True,
        ehr_id="1234567"
    )
    user = crud.user.create(db, obj_in=user_in)
    return user


@pytest.fixture(scope="function")
def normal_user(db: Session) -> models.User:
    """
    创建测试普通用户
    """
    # 普通用户数据
    user_in = schemas.UserCreate(
        name="普通用户",
        username="user",
        password="password123",
        is_superuser=False,
        ehr_id="7654321"
    )
    user = crud.user.create(db, obj_in=user_in)
    return user


@pytest.fixture(scope="function")
def team(db: Session, normal_user: models.User) -> models.Team:
    """
    创建测试团队
    """
    team_in = schemas.TeamCreate(
        name="测试团队",
        description="这是一个测试团队",
        department="测试部门"
    )
    from app.services.team.team_service import team_service
    team = team_service.create_team(db, team_in, normal_user.id)
    
    # 将普通用户添加到团队
    team_service.add_user_to_team(db, team.id, normal_user.id, normal_user.id)
    
    return team


@pytest.fixture(scope="function")
def role(db: Session, normal_user: models.User) -> models.Role:
    """
    创建测试角色
    """
    role_in = schemas.RoleCreate(
        name="测试角色",
        description="这是一个测试角色",
        permissions=["user:create", "user:read"]
    )
    role = crud.role.create(db, obj_in=role_in)
    return role


@pytest.fixture(scope="function")
def template(db: Session, normal_user: models.User) -> models.Template:
    """
    创建测试模板
    """
    template_in = schemas.TemplateCreate(
        name="测试模板",
        description="这是一个测试模板",
        department="测试部门",
        fields=[
            schemas.FieldCreate(
                name="字段1",
                label="测试字段1",
                type="text",
                required=True,
                order=1
            ),
            schemas.FieldCreate(
                name="字段2",
                label="测试字段2",
                type="number",
                required=False,
                order=2
            )
        ]
    )
    from app.services.template.template_service import template_service
    template = template_service.create_template(db, template_in, normal_user.id)
    return template


@pytest.fixture(scope="function")
def workflow(db: Session, template: models.Template, normal_user: models.User) -> models.Workflow:
    """
    创建测试工作流
    """
    workflow_in = schemas.WorkflowCreate(
        name="测试工作流",
        description="这是一个测试工作流",
        template_id=template.id,
    )
    from app.services.workflow.workflow_service import workflow_service
    workflow = workflow_service.create_workflow(db, workflow_in, normal_user.id)
    
    # 创建工作流节点
    node1_in = schemas.WorkflowNodeCreate(
        name="节点1",
        description="第一个节点",
        workflow_id=workflow.id,
        node_type="approval",
        order_index=1,
    )
    node1 = models.WorkflowNode(
        name=node1_in.name,
        description=node1_in.description,
        workflow_id=node1_in.workflow_id,
        node_type=node1_in.node_type,
        order_index=node1_in.order_index,
    )
    db.add(node1)
    db.flush()
    
    node2_in = schemas.WorkflowNodeCreate(
        name="节点2",
        description="第二个节点",
        workflow_id=workflow.id,
        node_type="approval",
        order_index=2,
        reject_to_node_id=node1.id
    )
    node2 = models.WorkflowNode(
        name=node2_in.name,
        description=node2_in.description,
        workflow_id=node2_in.workflow_id,
        node_type=node2_in.node_type,
        order_index=node2_in.order_index,
        reject_to_node_id=node2_in.reject_to_node_id,
    )
    db.add(node2)
    db.commit()
    
    return workflow


@pytest.fixture(scope="function")
def ledger(db: Session, template: models.Template, team: models.Team, normal_user: models.User) -> models.Ledger:
    """
    创建测试台账
    """
    ledger_in = schemas.LedgerCreate(
        name="测试台账",
        description="这是一个测试台账",
        team_id=team.id,
        template_id=template.id,
        data={"字段1": "测试值1", "字段2": 100}
    )
    from app.services.ledger.ledger_service import ledger_service
    ledger = ledger_service.create_ledger(db, ledger_in, normal_user)
    return ledger 