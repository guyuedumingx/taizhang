from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.crud.base import CRUDBase
from app.models.template import Template
from app.models.field import Field
from app.schemas.template import TemplateCreate, TemplateUpdate

class CRUDTemplate(CRUDBase[Template, TemplateCreate, TemplateUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Template]:
        return db.query(Template).filter(Template.name == name).first()
    
    def get_by_department(self, db: Session, *, department: str, skip: int = 0, limit: int = 100) -> List[Template]:
        return db.query(Template).filter(Template.department == department).offset(skip).limit(limit).all()
        
    def create(self, db: Session, *, obj_in: TemplateCreate, creator_id: int) -> Template:
        """创建模板，同时处理嵌套的字段创建"""
        # 从输入数据中提取字段列表
        fields = obj_in.fields
        
        # 移除 fields 字段，只保留模板相关数据
        obj_in_data = jsonable_encoder(obj_in)
        if "fields" in obj_in_data:
            del obj_in_data["fields"]
        
        # 创建模板实例
        db_obj = Template(**obj_in_data)
        db_obj.created_by_id = creator_id
        db_obj.updated_by_id = creator_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # 创建字段并关联到模板
        for field_data in fields:
            field_data_dict = jsonable_encoder(field_data)
            field_obj = Field(**field_data_dict)
            field_obj.template_id = db_obj.id
            db.add(field_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
        
    def update(self, db: Session, *, db_obj: Template, obj_in: Union[TemplateUpdate, Dict[str, Any]], updater_id: int) -> Template:
        """更新模板，同时设置更新者ID"""
        # 首先执行基本更新操作
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        # 设置更新者ID
        update_data["updated_by_id"] = updater_id
        
        # 更新模板实例
        for field in jsonable_encoder(db_obj):
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

template = CRUDTemplate(Template)
