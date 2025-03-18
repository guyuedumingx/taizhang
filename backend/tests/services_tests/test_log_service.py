import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app import models, schemas
from app.services.log.log_service import log_service
from app.utils.logger import LoggerService


def test_get_system_logs(db: Session, normal_user: models.User):
    """测试获取系统日志列表"""
    # 创建测试日志
    log1 = models.SystemLog(
        module="test",
        action="create",
        message="测试日志1",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    log2 = models.SystemLog(
        module="test",
        action="update",
        message="测试日志2",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    db.add(log1)
    db.add(log2)
    db.commit()
    
    # 创建查询参数
    params = schemas.LogQueryParams(
        module="test",
        level="info",
        skip=0,
        limit=100
    )
    
    # 获取日志列表
    logs = log_service.get_system_logs(db, params)
    
    # 验证结果
    assert len(logs) == 2
    assert logs[0].module == "test"
    assert logs[0].level == "info"
    assert logs[1].module == "test"
    assert logs[1].level == "info"
    
    # 测试按操作筛选
    params = schemas.LogQueryParams(
        module="test",
        action="create",
        level="info",
        skip=0,
        limit=100
    )
    logs = log_service.get_system_logs(db, params)
    assert len(logs) == 1
    assert logs[0].action == "create"


def test_count_system_logs(db: Session, normal_user: models.User):
    """测试统计系统日志数量"""
    # 创建测试日志
    log1 = models.SystemLog(
        module="count_test",
        action="create",
        message="统计测试日志1",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    log2 = models.SystemLog(
        module="count_test",
        action="update",
        message="统计测试日志2",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    log3 = models.SystemLog(
        module="count_test",
        action="delete",
        message="统计测试日志3",
        level="error",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    db.add(log1)
    db.add(log2)
    db.add(log3)
    db.commit()
    
    # 创建查询参数
    params = schemas.LogQueryParams(
        module="count_test",
        skip=0,
        limit=100
    )
    
    # 统计日志数量
    count = log_service.count_system_logs(db, params)
    
    # 验证结果
    assert count == 3
    
    # 测试按级别筛选
    params = schemas.LogQueryParams(
        module="count_test",
        level="error",
        skip=0,
        limit=100
    )
    count = log_service.count_system_logs(db, params)
    assert count == 1


def test_get_recent_system_logs(db: Session, normal_user: models.User):
    """测试获取最近的系统日志"""
    # 创建测试日志
    older_log = models.SystemLog(
        module="recent_test",
        action="create",
        message="较早的日志",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now() - timedelta(days=10)
    )
    recent_log = models.SystemLog(
        module="recent_test",
        action="update",
        message="最近的日志",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    db.add(older_log)
    db.add(recent_log)
    db.commit()
    
    # 获取最近7天的日志
    logs = log_service.get_recent_system_logs(db, days=7, limit=10)
    
    # 验证结果
    assert any(log.message == "最近的日志" for log in logs)
    assert not any(log.message == "较早的日志" for log in logs)


def test_get_error_logs(db: Session, normal_user: models.User):
    """测试获取错误日志"""
    # 创建测试日志
    info_log = models.SystemLog(
        module="error_test",
        action="create",
        message="信息日志",
        level="info",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    error_log = models.SystemLog(
        module="error_test",
        action="error",
        message="错误日志",
        level="error",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    db.add(info_log)
    db.add(error_log)
    db.commit()
    
    # 获取错误日志
    logs = log_service.get_error_logs(db, days=7, limit=10)
    
    # 验证结果
    assert any(log.message == "错误日志" and log.level == "error" for log in logs)
    assert not any(log.message == "信息日志" and log.level == "info" for log in logs)


def test_get_resource_logs(db: Session, normal_user: models.User):
    """测试获取指定资源的日志"""
    # 创建测试日志
    resource_log1 = models.SystemLog(
        module="resource_test",
        action="create",
        message="资源1日志",
        level="info",
        user_id=normal_user.id,
        resource_type="test_resource",
        resource_id="1",
        created_at=datetime.now()
    )
    resource_log2 = models.SystemLog(
        module="resource_test",
        action="update",
        message="资源2日志",
        level="info",
        user_id=normal_user.id,
        resource_type="test_resource",
        resource_id="2",
        created_at=datetime.now()
    )
    db.add(resource_log1)
    db.add(resource_log2)
    db.commit()
    
    # 获取资源日志
    logs = log_service.get_resource_logs(db, resource_type="test_resource", resource_id="1", limit=10)
    
    # 验证结果
    assert len(logs) == 1
    assert logs[0].resource_type == "test_resource"
    assert logs[0].resource_id == "1"
    assert logs[0].message == "资源1日志"


def test_get_audit_logs(db: Session, normal_user: models.User, ledger: models.Ledger):
    """测试获取审计日志"""
    # 创建测试审计日志
    audit_log1 = models.AuditLog(
        action="approve",
        comment="审批通过",
        user_id=normal_user.id,
        ledger_id=ledger.id,
        created_at=datetime.now()
    )
    audit_log2 = models.AuditLog(
        action="reject",
        comment="审批拒绝",
        user_id=normal_user.id,
        ledger_id=ledger.id,
        created_at=datetime.now()
    )
    db.add(audit_log1)
    db.add(audit_log2)
    db.commit()
    
    # 获取台账的审计日志
    logs = log_service.get_audit_logs(db, ledger_id=ledger.id, limit=10)
    
    # 验证结果
    assert len(logs) == 2
    assert logs[0].ledger_id == ledger.id
    assert logs[1].ledger_id == ledger.id
    
    # 获取用户的审计日志
    logs = log_service.get_audit_logs(db, user_id=normal_user.id, limit=10)
    
    # 验证结果
    assert len(logs) == 2
    assert logs[0].user_id == normal_user.id
    assert logs[1].user_id == normal_user.id


def test_get_ledger_audit_logs(db: Session, normal_user: models.User, ledger: models.Ledger):
    """测试获取特定台账的审计日志"""
    # 创建测试审计日志
    audit_log = models.AuditLog(
        action="submit",
        comment="提交台账",
        user_id=normal_user.id,
        ledger_id=ledger.id,
        created_at=datetime.now()
    )
    db.add(audit_log)
    db.commit()
    
    # 获取台账的审计日志
    logs = log_service.get_ledger_audit_logs(db, ledger_id=ledger.id, limit=10)
    
    # 验证结果
    assert len(logs) >= 1
    assert logs[0].ledger_id == ledger.id
    assert logs[0].action == "submit"
    
    # 测试不存在的台账
    with pytest.raises(Exception):
        log_service.get_ledger_audit_logs(db, ledger_id=999, limit=10)


def test_get_workflow_audit_logs(db: Session, normal_user: models.User, workflow: models.Workflow):
    """测试获取特定工作流的审计日志"""
    # 创建工作流实例
    instance = models.WorkflowInstance(
        workflow_id=workflow.id,
        ledger_id=1,  # 使用一个假的ledger_id
        created_by=normal_user.id,
        status="active"
    )
    db.add(instance)
    db.flush()
    
    # 创建测试审计日志
    audit_log = models.AuditLog(
        action="activate",
        comment="激活工作流",
        user_id=normal_user.id,
        workflow_instance_id=instance.id,
        created_at=datetime.now()
    )
    db.add(audit_log)
    db.commit()
    
    # 获取工作流的审计日志
    logs = log_service.get_workflow_audit_logs(db, workflow_id=workflow.id, limit=10)
    
    # 验证结果
    assert len(logs) >= 1
    assert logs[0].workflow_instance_id == instance.id
    assert logs[0].action == "activate"
    
    # 测试不存在的工作流
    with pytest.raises(Exception):
        log_service.get_workflow_audit_logs(db, workflow_id=999, limit=10)


def test_get_user_audit_logs(db: Session, normal_user: models.User):
    """测试获取特定用户的审计日志"""
    # 创建测试审计日志
    audit_log = models.AuditLog(
        action="login",
        comment="用户登录",
        user_id=normal_user.id,
        created_at=datetime.now()
    )
    db.add(audit_log)
    db.commit()
    
    # 获取用户的审计日志
    logs = log_service.get_user_audit_logs(db, user_id=normal_user.id, limit=10)
    
    # 验证结果
    assert len(logs) >= 1
    assert logs[0].user_id == normal_user.id
    assert logs[0].action == "login"
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        log_service.get_user_audit_logs(db, user_id=999, limit=10) 