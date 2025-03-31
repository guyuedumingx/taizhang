import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_get_logs(db: Session, admin_token_headers: dict):
    """测试获取日志列表"""
    # 创建一条测试日志
    log_in = schemas.LogCreate(
        level="INFO",
        module="test",
        action="test_action",
        message="测试日志",
        user_id=1
    )
    log = crud.log.create(db, obj_in=log_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/logs/",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(l["id"] == log.id for l in data)
    
    # 清理测试数据
    db.delete(log)
    db.commit()


def test_get_logs_with_filter(db: Session, admin_token_headers: dict):
    """测试带过滤条件获取日志列表"""
    # 创建一条测试日志
    log_in = schemas.LogCreate(
        level="ERROR",
        module="test_filter",
        action="test_filter_action",
        message="测试过滤日志",
        user_id=1
    )
    log = crud.log.create(db, obj_in=log_in)
    
    # 按级别过滤
    response = client.get(
        f"{settings.API_V1_STR}/logs/?level=ERROR",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(l["level"] == "ERROR" for l in data)
    
    # 按模块过滤
    response = client.get(
        f"{settings.API_V1_STR}/logs/?module=test_filter",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(l["module"] == "test_filter" for l in data)
    
    # 清理测试数据
    db.delete(log)
    db.commit()


def test_get_log(db: Session, admin_token_headers: dict):
    """测试获取单个日志详情"""
    # 创建一条测试日志
    log_in = schemas.LogCreate(
        level="INFO",
        module="test_detail",
        action="test_detail_action",
        message="测试日志详情",
        user_id=1
    )
    log = crud.log.create(db, obj_in=log_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/logs/{log.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log.id
    assert data["level"] == log.level
    assert data["module"] == log.module
    assert data["action"] == log.action
    assert data["message"] == log.message
    
    # 清理测试数据
    db.delete(log)
    db.commit()


def test_search_logs(db: Session, admin_token_headers: dict):
    """测试搜索日志"""
    # 创建一条测试日志
    log_in = schemas.LogCreate(
        level="INFO",
        module="test_search",
        action="test_search_action",
        message="测试搜索日志内容",
        user_id=1
    )
    log = crud.log.create(db, obj_in=log_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/logs/search?query=搜索日志",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(l["id"] == log.id for l in data)
    
    # 清理测试数据
    db.delete(log)
    db.commit()


def test_get_user_logs(db: Session, admin_token_headers: dict, normal_user: models.User):
    """测试获取指定用户的日志"""
    # 创建一条测试日志
    log_in = schemas.LogCreate(
        level="INFO",
        module="test_user",
        action="test_user_action",
        message="测试用户日志",
        user_id=normal_user.id
    )
    log = crud.log.create(db, obj_in=log_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/logs/user/{normal_user.id}",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(l["user_id"] == normal_user.id for l in data)
    assert any(l["id"] == log.id for l in data)
    
    # 清理测试数据
    db.delete(log)
    db.commit()


def test_get_module_actions(db: Session, admin_token_headers: dict):
    """测试获取模块操作列表"""
    # 创建几条测试日志，不同的模块和操作
    log1_in = schemas.LogCreate(
        level="INFO",
        module="test_module1",
        action="test_action1",
        message="测试模块操作1",
        user_id=1
    )
    log1 = crud.log.create(db, obj_in=log1_in)
    
    log2_in = schemas.LogCreate(
        level="INFO",
        module="test_module1",
        action="test_action2",
        message="测试模块操作2",
        user_id=1
    )
    log2 = crud.log.create(db, obj_in=log2_in)
    
    response = client.get(
        f"{settings.API_V1_STR}/logs/modules",
        headers=admin_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "test_module1" in data
    assert "test_action1" in data["test_module1"]
    assert "test_action2" in data["test_module1"]
    
    # 清理测试数据
    db.delete(log1)
    db.delete(log2)
    db.commit()
