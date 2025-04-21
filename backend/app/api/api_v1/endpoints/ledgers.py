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
from app.services.ledger_service import ledger_service

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
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账列表
    """
    # 检查权限
    # if not deps.check_permissions("ledger", "view", current_user):
    #     raise HTTPException(status_code=403, detail="没有足够的权限")
    
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
    # if not deps.check_permissions("ledger", "view", current_user):
    #     raise HTTPException(status_code=403, detail="没有足够的权限")
    
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


@router.get("/{ledger_id}/field-values", response_model=List[schemas.FieldValue])
def get_ledger_field_values(
    *,
    ledger_id: int = Path(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账的所有字段值
    """
    # 检查权限
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账是否存在
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能查看自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        # 检查用户是否是创建者
        if ledger.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权查看此台账的字段值")
    
    # 获取台账字段值
    field_values = crud.field_value.get_by_ledger(db, ledger_id=ledger_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="view_field_values",
        message=f"查看台账{ledger.name}的字段值",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id)
    )
    
    return field_values


@router.put("/{ledger_id}/field-values/{field_value_id}", response_model=schemas.FieldValue)
def update_ledger_field_value(
    *,
    ledger_id: int = Path(...),
    field_value_id: int = Path(...),
    field_value_in: schemas.FieldValueUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新台账字段值
    """
    # 检查权限
    if not deps.check_permissions("ledger", "update", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账是否存在
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能更新自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        # 检查用户是否是创建者
        if ledger.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权更新此台账的字段值")
    
    # 检查字段值是否存在且属于该台账
    field_value = db.query(models.FieldValue).filter(
        models.FieldValue.id == field_value_id,
        models.FieldValue.ledger_id == ledger_id
    ).first()
    if not field_value:
        raise HTTPException(status_code=404, detail="字段值不存在或不属于该台账")
    
    # 更新字段值
    field_value = crud.field_value.update(db, db_obj=field_value, obj_in=field_value_in)
    
    # 同步ledger的data字段
    ledger_service.sync_ledger_data_with_field_values(db, ledger_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="update_field_value",
        message=f"更新台账{ledger.name}的字段值",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id)
    )
    
    return field_value


@router.post("/{ledger_id}/field-values", response_model=schemas.FieldValue)
def create_ledger_field_value(
    *,
    ledger_id: int = Path(...),
    field_value_in: schemas.FieldValueCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建台账字段值
    """
    # 检查权限
    if not deps.check_permissions("ledger", "update", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账是否存在
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能为自己团队的台账创建字段值
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        # 检查用户是否是创建者
        if ledger.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权为此台账创建字段值")
    
    # 检查字段是否存在
    field = db.query(models.Field).filter(models.Field.id == field_value_in.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    
    # 检查字段是否属于该台账的模板
    if field.template_id != ledger.template_id:
        raise HTTPException(status_code=400, detail="字段不属于该台账的模板")
    
    # 检查是否已存在该字段的值
    existing_field_value = crud.field_value.get_by_ledger_and_field(
        db,
        ledger_id=ledger_id,
        field_id=field_value_in.field_id
    )
    if existing_field_value:
        raise HTTPException(status_code=400, detail="该字段已有值，请使用更新接口")
    
    # 创建字段值
    field_value = crud.field_value.create(db, obj_in=field_value_in, ledger_id=ledger_id)
    
    # 同步ledger的data字段
    ledger_service.sync_ledger_data_with_field_values(db, ledger_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="create_field_value",
        message=f"为台账{ledger.name}创建字段值",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id)
    )
    
    return field_value


@router.get("/{ledger_id}/sync-field-values", response_model=List[schemas.FieldValue])
def sync_field_values(
    *,
    ledger_id: int = Path(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    同步台账数据和字段值
    如果台账有data字段，将其同步到field_values表中
    """
    # 检查权限
    if not deps.check_permissions("ledger", "update", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账是否存在
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能同步自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        # 检查用户是否是创建者
        if ledger.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权同步此台账数据")
    
    # 执行同步
    field_values = ledger_service.sync_field_values_with_ledger_data(db, ledger_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="sync_field_values",
        message=f"同步台账{ledger.name}的数据和字段值",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id)
    )
    
    return field_values 