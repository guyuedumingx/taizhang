from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService
from app.services.log.log_service import log_service

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
    logs = log_service.get_system_logs(db, params=params)
    
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
    count = log_service.count_system_logs(db, params=params)
    
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
    logs = log_service.get_recent_system_logs(db, days=days, limit=limit)
    
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
    logs = log_service.get_error_logs(db, days=days, limit=limit)
    
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
    logs = log_service.get_resource_logs(
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
    logs = log_service.get_audit_logs(
        db, 
        ledger_id=ledger_id, 
        workflow_instance_id=workflow_instance_id, 
        user_id=user_id, 
        limit=limit
    )
    
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
    
    # 获取审计日志
    logs = log_service.get_ledger_audit_logs(db, ledger_id=ledger_id, limit=limit)
    
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
    
    # 获取审计日志
    logs = log_service.get_workflow_audit_logs(db, workflow_id=workflow_id, limit=limit)
    
    return logs


@router.get("/audit/user/{user_id}", response_model=List[schemas.AuditLog])
def read_user_audit_logs(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int = Path(..., title="用户ID"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取特定用户的审计日志
    """
    # 检查权限
    if not deps.check_permissions("log", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取审计日志
    logs = log_service.get_user_audit_logs(db, user_id=user_id, limit=limit)
    
    return logs 