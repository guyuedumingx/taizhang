from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class AutoFillTriggerConfig(Base):
    __tablename__ = "auto_fill_trigger_configs"

    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, nullable=False, unique=True, index=True)
    api_url = Column(String, nullable=False)
    headers = Column(JSON, nullable=True, default=dict)
    timeout = Column(Integer, default=5)
    retry_times = Column(Integer, default=3)
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
