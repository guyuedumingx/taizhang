from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    label = Column(String, nullable=True)
    type = Column(String, nullable=False)  # input, textarea, select, date, number
    required = Column(Boolean, default=False)
    options = Column(JSON, nullable=True)  # 用于select类型的选项
    default_value = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_key_field = Column(Boolean, default=True)  # 是否为关键字段，默认为是
    
    # 外键
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    
    # 关系
    template = relationship("Template", back_populates="fields")
    field_values = relationship("FieldValue", back_populates="field", cascade="all, delete-orphan") 