from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Response
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from datetime import datetime
from urllib.parse import quote

from app import models, schemas, crud
from app.api import deps
from app.utils.logger import LoggerService
from app.services.ledger.ledger_service import ledger_service

router = APIRouter()


@router.get("/", response_model=List[schemas.Ledger])
def read_ledgers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = None,
    template_id: Optional[int] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账列表
    """
    # 检查权限
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取台账列表
    ledgers = ledger_service.get_ledgers(
        db,
        skip=skip,
        limit=limit,
        team_id=team_id,
        template_id=template_id,
        search=search,
        status=status,
        approval_status=approval_status,
        workflow_id=workflow_id,
        current_user=current_user
    )
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="list",
        message="查询台账列表",
        user_id=current_user.id,
    )
    
    return ledgers


@router.post("/", response_model=schemas.Ledger)
def create_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_in: schemas.LedgerCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 创建台账
    ledger = ledger_service.create_ledger(db, ledger_in, current_user)
    
    return ledger


@router.get("/{ledger_id}", response_model=schemas.Ledger)
def read_ledger(
    ledger_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账详情
    """
    # 检查权限
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取台账
    ledger = ledger_service.get_ledger(db, ledger_id, current_user)
    
    return ledger


@router.put("/{ledger_id}", response_model=schemas.Ledger)
def update_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int,
    ledger_in: schemas.LedgerUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "update", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 更新台账
    ledger = ledger_service.update_ledger(db, ledger_id, ledger_in, current_user)
    
    return ledger


@router.delete("/{ledger_id}", response_model=schemas.Ledger)
def delete_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 删除台账
    ledger = ledger_service.delete_ledger(db, ledger_id, current_user)
    
    return ledger


@router.get("/{ledger_id}/export", response_class=Response)
def export_ledger(
    *,
    ledger_id: int = Path(...),
    format: str = Query(..., description="导出格式，支持excel、csv、txt"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "export", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 导出台账
    file_data, filename, content_type = ledger_service.export_ledger(db, ledger_id, format, current_user)
    
    # 设置响应头
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(filename)}"',
        "Content-Type": content_type
    }
    
    return Response(content=file_data.getvalue(), headers=headers)


@router.get("/export-all", response_class=Response)
def export_all_ledgers(
    *,
    format: str = Query(..., description="导出格式，支持excel、csv、txt"),
    template_id: Optional[int] = Query(None, description="模板ID，用于筛选特定模板的台账"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出所有台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "export", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 导出所有台账
    file_data, filename, content_type = ledger_service.export_all_ledgers(db, format, template_id, current_user)
    
    # 设置响应头
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(filename)}"',
        "Content-Type": content_type
    }
    
    return Response(content=file_data.getvalue(), headers=headers) 