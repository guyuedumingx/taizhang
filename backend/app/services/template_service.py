from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas

class TemplateService:
    @staticmethod
    def get_templates(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[models.Template]:
        """
        获取模板列表
        """
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

    @staticmethod
    def create_template(
        db: Session,
        template_in: schemas.TemplateCreate,
        current_user_id: int
    ) -> models.Template:
        """
        创建新模板
        """
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
            workflow_id=template_in.workflow_id,
            created_by_id=current_user_id,
            updated_by_id=current_user_id,
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

    @staticmethod
    def get_template(db: Session, template_id: int) -> models.Template:
        """
        获取模板详情
        """
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

    @staticmethod
    def update_template(
        db: Session,
        template_id: int,
        template_in: schemas.TemplateUpdate,
        current_user_id: int
    ) -> models.Template:
        """
        更新模板信息
        """
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
        template.updated_by_id = current_user_id
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # 处理字段更新
        if hasattr(template_in, "fields") and template_in.fields is not None:
            # 获取现有字段
            existing_fields = db.query(models.Field).filter(models.Field.template_id == template.id).all()
            existing_field_ids = {field.id for field in existing_fields if field.id is not None}
            
            # 新字段ID
            updated_field_ids = set()
            
            # 更新或创建字段
            for field_data in template_in.fields:
                if field_data.id:
                    # 更新现有字段
                    field = db.query(models.Field).filter(models.Field.id == field_data.id).first()
                    if field and field.template_id == template.id:
                        # 更新字段属性
                        field.name = field_data.name
                        field.label = field_data.label
                        field.type = field_data.type
                        field.required = field_data.required
                        field.options = field_data.options
                        field.default_value = field_data.default_value
                        field.order = field_data.order
                        
                        db.add(field)
                        updated_field_ids.add(field.id)
                else:
                    # 创建新字段
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
            
            # 删除不再使用的字段
            fields_to_delete = existing_field_ids - updated_field_ids
            for field_id in fields_to_delete:
                field = db.query(models.Field).filter(models.Field.id == field_id).first()
                if field:
                    db.delete(field)
            
            db.commit()
        
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

    @staticmethod
    def delete_template(db: Session, template_id: int) -> models.Template:
        """
        删除模板
        """
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 检查是否有关联的台账
        ledgers = db.query(models.Ledger).filter(models.Ledger.template_id == template_id).count()
        if ledgers > 0:
            raise HTTPException(status_code=400, detail="该模板已被台账使用，无法删除")
        
        # 删除字段
        db.query(models.Field).filter(models.Field.template_id == template_id).delete()
        
        # 删除模板
        db.delete(template)
        db.commit()
        
        return template


template_service = TemplateService() 