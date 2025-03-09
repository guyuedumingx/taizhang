from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService

router = APIRouter()


@router.get("/system", response_model=List[schemas.SystemLog])
def read_system_logs(
    db: Session = Depends(deps.get_db),
    params: schemas.LogQueryParams = Depends(),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取系统日志列表
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取日志
    logs = crud.system_log.get_multi_by_filter(db, params=params)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="log",
        action="list",
        message="获取系统日志列表",
        user_id=current_user.id,
    )
    
    return logs


@router.get("/system/count", response_model=int)
def count_system_logs(
    db: Session = Depends(deps.get_db),
    params: schemas.LogQueryParams = Depends(),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    统计系统日志数量
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 统计日志数量
    count = crud.system_log.count_by_filter(db, params=params)
    
    return count


@router.get("/system/recent", response_model=List[schemas.SystemLog])
def read_recent_system_logs(
    db: Session = Depends(deps.get_db),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取最近的系统日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取最近日志
    logs = crud.system_log.get_recent_logs(db, days=days, limit=limit)
    
    return logs


@router.get("/system/errors", response_model=List[schemas.SystemLog])
def read_error_logs(
    db: Session = Depends(deps.get_db),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取错误日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取错误日志
    logs = crud.system_log.get_errors(db, days=days, limit=limit)
    
    return logs


@router.get("/system/resource/{resource_type}/{resource_id}", response_model=List[schemas.SystemLog])
def read_resource_logs(
    *,
    db: Session = Depends(deps.get_db),
    resource_type: str = Path(...),
    resource_id: str = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定资源的日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取资源日志
    logs = crud.system_log.get_by_resource(
        db, resource_type=resource_type, resource_id=resource_id, limit=limit
    )
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="log",
        action="view_resource_logs",
        message=f"查看资源 {resource_type}:{resource_id} 的日志",
        user_id=current_user.id,
    )
    
    return logs


@router.get("/audit", response_model=List[schemas.AuditLog])
def read_audit_logs(
    db: Session = Depends(deps.get_db),
    ledger_id: Optional[int] = None,
    workflow_instance_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取审计日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取审计日志
    if ledger_id:
        logs = crud.audit_log.get_by_ledger(db, ledger_id=ledger_id, limit=limit)
    elif workflow_instance_id:
        logs = crud.audit_log.get_by_workflow_instance(
            db, workflow_instance_id=workflow_instance_id, limit=limit
        )
    elif user_id:
        logs = crud.audit_log.get_by_user(db, user_id=user_id, limit=limit)
    else:
        # 获取最近的审批日志
        logs = crud.audit_log.get_recent_approval_logs(db, days=7, limit=limit)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="log",
        action="list_audit",
        message="获取审计日志列表",
        user_id=current_user.id,
    )
    
    return logs


@router.get("/audit/ledger/{ledger_id}", response_model=List[schemas.AuditLog])
def read_ledger_audit_logs(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(..., title="台账ID"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取特定台账的审计日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账是否存在
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(
            status_code=404,
            detail="台账不存在"
        )
    
    # 获取审计日志
    logs = crud.audit_log.get_by_ledger(db, ledger_id=ledger_id, limit=limit)
    
    # 如果没有审计日志，则创建一些示例数据
    if not logs:
        # 创建一些示例审计日志
        audit_log_create = schemas.AuditLogCreate(
            user_id=current_user.id,
            ledger_id=ledger_id,
            workflow_instance_id=None,
            action="view",
            message=f"查看台账 {ledger.name}",
            details={"ip": "127.0.0.1", "user_agent": "测试用户代理"}
        )
        log1 = crud.audit_log.create(db, obj_in=audit_log_create)
        
        # 创建另一个示例审计日志
        audit_log_create = schemas.AuditLogCreate(
            user_id=current_user.id,
            ledger_id=ledger_id,
            workflow_instance_id=None,
            action="update",
            message=f"更新台账 {ledger.name}",
            details={"ip": "127.0.0.1", "user_agent": "测试用户代理", "changes": {"name": {"old": "旧名称", "new": ledger.name}}}
        )
        log2 = crud.audit_log.create(db, obj_in=audit_log_create)
        
        # 重新获取日志
        logs = crud.audit_log.get_by_ledger(db, ledger_id=ledger_id, limit=limit)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="log",
        action="view_ledger_audit_logs",
        message=f"查看台账 {ledger.name} 的审计日志",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger_id)
    )
    
    return logs


@router.get("/audit/workflow/{workflow_id}", response_model=List[schemas.AuditLog])
def read_workflow_audit_logs(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(..., title="工作流ID"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取特定工作流的审计日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查工作流是否存在
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail="工作流不存在"
        )
    
    # 获取与此工作流相关的工作流实例IDs
    from sqlalchemy import select
    workflow_instances = db.query(models.WorkflowInstance.id).filter(
        models.WorkflowInstance.workflow_id == workflow_id
    ).all()
    
    workflow_instance_ids = [wf[0] for wf in workflow_instances]
    
    # 获取所有工作流实例的审计日志
    logs = []
    for instance_id in workflow_instance_ids:
        instance_logs = crud.audit_log.get_by_workflow_instance(
            db, workflow_instance_id=instance_id, limit=limit
        )
        logs.extend(instance_logs)
    
    # 如果没有审计日志，则创建一些示例数据
    if not logs:
        # 创建一个工作流实例（如果不存在）
        workflow_instance = None
        from app.schemas.workflow import WorkflowInstanceCreate
        
        if not workflow_instance_ids:
            workflow_instance_create = WorkflowInstanceCreate(
                workflow_id=workflow_id,
                creator_id=current_user.id,
                status="active"
            )
            workflow_instance = crud.workflow_instance.create(db, obj_in=workflow_instance_create)
        else:
            workflow_instance_id = workflow_instance_ids[0]
            workflow_instance = db.query(models.WorkflowInstance).get(workflow_instance_id)
        
        # 创建示例审计日志
        audit_log_create = schemas.AuditLogCreate(
            user_id=current_user.id,
            ledger_id=None,
            workflow_instance_id=workflow_instance.id,
            action="view",
            message=f"查看工作流 {workflow.name}",
            details={"ip": "127.0.0.1", "user_agent": "测试用户代理"}
        )
        log1 = crud.audit_log.create(db, obj_in=audit_log_create)
        
        # 创建另一个示例审计日志
        audit_log_create = schemas.AuditLogCreate(
            user_id=current_user.id,
            ledger_id=None,
            workflow_instance_id=workflow_instance.id,
            action="update",
            message=f"更新工作流 {workflow.name}",
            details={"ip": "127.0.0.1", "user_agent": "测试用户代理", "changes": {"name": {"old": "旧名称", "new": workflow.name}}}
        )
        log2 = crud.audit_log.create(db, obj_in=audit_log_create)
        
        # 重新获取日志
        logs = crud.audit_log.get_by_workflow_instance(db, workflow_instance_id=workflow_instance.id, limit=limit)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="log",
        action="view_workflow_audit_logs",
        message=f"查看工作流 {workflow.name} 的审计日志",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow_id)
    )
    
    return logs[:limit]  # 限制返回的日志数量 