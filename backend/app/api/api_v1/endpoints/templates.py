from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.api import deps
from app.services.template_service import template_service

router = APIRouter()


@router.get("/", response_model=List[schemas.Template])
def read_templates(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取模板列表
    """
    # 检查权限
    if not deps.check_permissions("template", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return template_service.get_templates(db, skip=skip, limit=limit, search=search)


@router.post("/", response_model=schemas.Template)
def create_template(
    *,
    db: Session = Depends(deps.get_db),
    template_in: schemas.TemplateCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新模板
    """
    # 检查权限
    if not deps.check_permissions("template", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return template_service.create_template(db, template_in=template_in, current_user_id=current_user.id)


@router.get("/{template_id}", response_model=schemas.TemplateDetail)
def read_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取模板详情
    """
    # 检查权限
    if not deps.check_permissions("template", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return template_service.get_template(db, template_id=template_id)


@router.put("/{template_id}", response_model=schemas.Template)
def update_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    template_in: schemas.TemplateUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新模板信息
    """
    # 检查权限
    if not deps.check_permissions("template", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return template_service.update_template(
        db, 
        template_id=template_id, 
        template_in=template_in, 
        current_user_id=current_user.id
    )


@router.delete("/{template_id}", response_model=schemas.Template)
def delete_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除模板
    """
    # 检查权限
    if not deps.check_permissions("template", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    return template_service.delete_template(db, template_id=template_id)


@router.get("/{template_id}/fields", response_model=List[schemas.Field])
def read_template_fields(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取模板字段列表
    """
    # 检查权限
    if not deps.check_permissions("template", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 获取字段
    fields = db.query(models.Field).filter(models.Field.template_id == template.id).order_by(models.Field.order).all()
    
    return fields


@router.post("/{template_id}/fields", response_model=schemas.Field)
def create_template_field(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    field_in: schemas.FieldCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建模板字段
    """
    # 检查权限
    if not deps.check_permissions("template", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 检查字段名称是否已存在
    field = db.query(models.Field).filter(
        models.Field.template_id == template_id,
        models.Field.name == field_in.name
    ).first()
    if field:
        raise HTTPException(
            status_code=400,
            detail="字段名称已存在",
        )
    
    # 获取最大排序值
    max_order = db.query(models.Field).filter(
        models.Field.template_id == template_id
    ).order_by(models.Field.order.desc()).first()
    
    # 创建字段
    field = models.Field(
        name=field_in.name,
        label=field_in.label,
        type=field_in.type,
        required=field_in.required,
        options=field_in.options,
        default_value=field_in.default_value,
        order=max_order.order + 1 if max_order else 1,
        template_id=template_id,
    )
    db.add(field)
    
    # 更新模板更新时间
    template.updated_by_id = current_user.id
    db.add(template)
    
    db.commit()
    db.refresh(field)
    
    return field


@router.put("/{template_id}/fields/{field_id}", response_model=schemas.Field)
def update_template_field(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    field_id: int,
    field_in: schemas.FieldUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新模板字段
    """
    # 检查权限
    if not deps.check_permissions("template", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    field = db.query(models.Field).filter(
        models.Field.id == field_id,
        models.Field.template_id == template_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    
    # 如果更新字段名称，检查是否已存在
    if field_in.name and field_in.name != field.name:
        existing_field = db.query(models.Field).filter(
            models.Field.template_id == template_id,
            models.Field.name == field_in.name
        ).first()
        if existing_field:
            raise HTTPException(
                status_code=400,
                detail="字段名称已存在",
            )
    
    # 更新字段信息
    update_data = field_in.dict(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(field, field_name, value)
    
    # 更新模板更新时间
    template.updated_by_id = current_user.id
    db.add(template)
    
    db.add(field)
    db.commit()
    db.refresh(field)
    
    return field


@router.delete("/{template_id}/fields/{field_id}", response_model=schemas.Field)
def delete_template_field(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    field_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除模板字段
    """
    # 检查权限
    if not deps.check_permissions("template", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    field = db.query(models.Field).filter(
        models.Field.id == field_id,
        models.Field.template_id == template_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    
    # 检查是否有台账使用该模板
    ledger_count = db.query(models.Ledger).filter(models.Ledger.template_id == template.id).count()
    if ledger_count > 0:
        raise HTTPException(status_code=400, detail="有台账正在使用该模板，不能删除字段")
    
    # 更新模板更新时间
    template.updated_by_id = current_user.id
    db.add(template)
    
    # 删除字段
    db.delete(field)
    db.commit()
    
    return field 