from typing import Any, List, Optional, Dict
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

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
        
        # 使用预加载优化查询，避免N+1问题
        query = query.options(
            selectinload(models.Template.creator),  # 预加载创建人
            selectinload(models.Template.updater),  # 预加载更新人
        )
        
        # 分页
        templates = query.offset(skip).limit(limit).all()
        
        # 批量获取字段数量（避免N+1查询）
        template_ids = [t.id for t in templates]
        field_counts = defaultdict(int)
        if template_ids:
            from sqlalchemy import func
            field_count_query = db.query(
                models.Field.template_id,
                func.count(models.Field.id).label('count')
            ).filter(
                models.Field.template_id.in_(template_ids)
            ).group_by(models.Field.template_id).all()
            
            for template_id, count in field_count_query:
                field_counts[template_id] = count
        
        # 设置关联信息
        for template in templates:
            # 获取创建者姓名（已预加载）
            if template.creator:
                template.created_by_name = template.creator.name
            else:
                template.created_by_name = None
            
            # 获取更新者姓名（已预加载）
            if template.updater:
                template.updated_by_name = template.updater.name
            else:
                template.updated_by_name = None
            
            # 获取字段数量（从批量查询结果获取）
            template.field_count = field_counts.get(template.id, 0)
            
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
            default_description=getattr(template_in, "default_description", None),
            default_metadata=getattr(template_in, "default_metadata", None),
            auto_fill_config=getattr(template_in, "auto_fill_config", None),
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
        
        # 使用预加载获取关联信息
        db.refresh(template, ['creator', 'updater'])
        
        # 获取创建者姓名（已预加载）
        if template.creator:
            template.created_by_name = template.creator.name
        else:
            template.created_by_name = None
        
        # 获取更新者姓名（已预加载）
        if template.updater:
            template.updated_by_name = template.updater.name
        else:
            template.updated_by_name = None
        
        # 使用已创建字段数量，避免额外统计查询
        template.field_count = len(template_in.fields or [])
        
        return template

    @staticmethod
    def get_template(db: Session, template_id: int) -> models.Template:
        """
        获取模板详情
        """
        # 使用预加载优化查询
        template = db.query(models.Template).filter(models.Template.id == template_id).options(
            selectinload(models.Template.creator),  # 预加载创建人
            selectinload(models.Template.updater),  # 预加载更新人
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 获取关联信息（已预加载）
        if template.creator:
            template.created_by_name = template.creator.name
        else:
            template.created_by_name = None
        
        if template.updater:
            template.updated_by_name = template.updater.name
        else:
            template.updated_by_name = None
        
        # 获取字段
        fields = db.query(models.Field).filter(models.Field.template_id == template.id).order_by(models.Field.order).all()
        template.fields = fields
        template.field_count = len(fields)

        # 从配置文件中查找该模板中哪些字段名配置了自动填充触发
        from app.core.auto_fill_trigger_loader import get_trigger_field_names
        all_trigger_names = set(get_trigger_field_names())
        field_names = [f.name for f in fields if f.name]
        template.auto_fill_trigger_fields = [n for n in field_names if n in all_trigger_names]

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
        
        # 刷新模板以加载关联（如果还没有加载）
        db.refresh(template, ['creator', 'updater'])
        
        # 获取关联信息（已预加载）
        if template.creator:
            template.created_by_name = template.creator.name
        else:
            template.created_by_name = None
        
        if template.updater:
            template.updated_by_name = template.updater.name
        else:
            template.updated_by_name = None
        
        # 获取字段
        fields = db.query(models.Field).filter(models.Field.template_id == template.id).order_by(models.Field.order).all()
        template.fields = fields
        template.field_count = len(fields)
        
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