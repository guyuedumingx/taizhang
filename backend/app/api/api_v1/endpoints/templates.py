from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps

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
    
    # 构建查询
    query = db.query(models.Template)
    
    # 搜索
    if search:
        query = query.filter(models.Template.name.ilike(f"%{search}%"))
    
    # 获取总数
    total = query.count()
    
    # 分页
    templates = query.offset(skip).limit(limit).all()
    
    # 获取关联信息
    for template in templates:
        # 获取创建者和更新者信息
        if template.created_by_id:
            creator = db.query(models.User).filter(models.User.id == template.created_by_id).first()
            template.created_by_name = creator.name if creator else None
        
        if template.updated_by_id:
            updater = db.query(models.User).filter(models.User.id == template.updated_by_id).first()
            template.updated_by_name = updater.name if updater else None
        
        # 获取字段数量
        template.field_count = db.query(models.Field).filter(models.Field.template_id == template.id).count()
    
    return templates


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
    
    # 检查模板名称是否已存在
    template = db.query(models.Template).filter(models.Template.name == template_in.name).first()
    if template:
        raise HTTPException(
            status_code=400,
            detail="模板名称已存在",
        )
    
    # 创建模板
    template = models.Template(
        name=template_in.name,
        description=template_in.description,
        department=template_in.department,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # 创建字段
    if template_in.fields:
        for field_data in template_in.fields:
            field = models.Field(
                name=field_data.name,
                label=field_data.label,
                type=field_data.type,
                required=field_data.required,
                options=field_data.options,
                default_value=field_data.default_value,
                order=field_data.order,
                template_id=template.id,
            )
            db.add(field)
        db.commit()
    
    # 获取关联信息
    if template.created_by_id:
        creator = db.query(models.User).filter(models.User.id == template.created_by_id).first()
        template.created_by_name = creator.name if creator else None
    
    if template.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == template.updated_by_id).first()
        template.updated_by_name = updater.name if updater else None
    
    # 获取字段数量
    template.field_count = db.query(models.Field).filter(models.Field.template_id == template.id).count()
    
    return template


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
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 获取关联信息
    if template.created_by_id:
        creator = db.query(models.User).filter(models.User.id == template.created_by_id).first()
        template.created_by_name = creator.name if creator else None
    
    if template.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == template.updated_by_id).first()
        template.updated_by_name = updater.name if updater else None
    
    # 获取字段
    fields = db.query(models.Field).filter(models.Field.template_id == template.id).order_by(models.Field.order).all()
    template.fields = fields
    
    return template


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
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 如果更新模板名称，检查是否已存在
    if template_in.name and template_in.name != template.name:
        existing_template = db.query(models.Template).filter(models.Template.name == template_in.name).first()
        if existing_template:
            raise HTTPException(
                status_code=400,
                detail="模板名称已存在",
            )
    
    # 更新模板信息
    update_data = template_in.dict(exclude_unset=True, exclude={"fields"})
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(template, field, value)
    
    # 更新更新者和更新时间
    template.updated_by_id = current_user.id
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # 处理字段更新
    if hasattr(template_in, "fields") and template_in.fields is not None:
        # 获取现有字段
        existing_fields = db.query(models.Field).filter(models.Field.template_id == template.id).all()
        existing_field_ids = {field.id for field in existing_fields if field.id is not None}
        
        # 处理新字段和更新字段
        for field_data in template_in.fields:
            if hasattr(field_data, "id") and field_data.id:
                # 更新现有字段
                field = db.query(models.Field).filter(
                    models.Field.id == field_data.id,
                    models.Field.template_id == template.id
                ).first()
                
                if field:
                    # 更新字段
                    field_update = field_data.dict(exclude_unset=True)
                    for field_attr, value in field_update.items():
                        setattr(field, field_attr, value)
                    
                    db.add(field)
                    existing_field_ids.discard(field.id)  # 从待删除集合中移除
            else:
                # 创建新字段
                field = models.Field(
                    template_id=template.id,
                    name=field_data.name,
                    label=field_data.label,
                    type=field_data.type,
                    required=field_data.required,
                    options=field_data.options,
                    default_value=field_data.default_value,
                    order=field_data.order,
                    is_key_field=field_data.is_key_field
                )
                db.add(field)
        
        # 删除不再存在的字段
        for field_id in existing_field_ids:
            db.query(models.Field).filter(models.Field.id == field_id).delete()
        
        db.commit()
    
    # 获取关联信息
    if template.created_by_id:
        creator = db.query(models.User).filter(models.User.id == template.created_by_id).first()
        template.created_by_name = creator.name if creator else None
    
    if template.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == template.updated_by_id).first()
        template.updated_by_name = updater.name if updater else None
    
    # 获取字段数量
    template.field_count = db.query(models.Field).filter(models.Field.template_id == template.id).count()
    
    return template


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
    
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 检查是否有台账使用该模板
    ledger_count = db.query(models.Ledger).filter(models.Ledger.template_id == template.id).count()
    if ledger_count > 0:
        raise HTTPException(status_code=400, detail="有台账正在使用该模板，不能删除")
    
    # 获取关联信息用于返回
    if template.created_by_id:
        creator = db.query(models.User).filter(models.User.id == template.created_by_id).first()
        template.created_by_name = creator.name if creator else None
    
    if template.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == template.updated_by_id).first()
        template.updated_by_name = updater.name if updater else None
    
    # 获取字段数量
    template.field_count = db.query(models.Field).filter(models.Field.template_id == template.id).count()
    
    # 删除字段
    db.query(models.Field).filter(models.Field.template_id == template.id).delete()
    
    # 删除模板
    db.delete(template)
    db.commit()
    
    return template


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