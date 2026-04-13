"""自动填充触发配置 Schema：字段名→API 映射的管理。"""
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AutoFillTriggerConfigBase(BaseModel):
    field_name: str = Field(..., description="触发自动填充的字段名")
    api_url: str = Field(..., description="外部 API 地址")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    timeout: Optional[int] = Field(5, description="超时时间（秒）")
    retry_times: Optional[int] = Field(3, description="重试次数")
    enabled: Optional[bool] = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="配置说明")


class AutoFillTriggerConfigCreate(AutoFillTriggerConfigBase):
    field_name: str
    api_url: str


class AutoFillTriggerConfigUpdate(BaseModel):
    field_name: Optional[str] = None
    api_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None
    retry_times: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class AutoFillTriggerConfig(AutoFillTriggerConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
