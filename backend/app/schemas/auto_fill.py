"""自动填充相关 Schema：请求体和响应。"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AutoFillRequest(BaseModel):
    """自动填充接口请求体。"""
    field_name: str = Field(..., description="触发填充的字段名")
    field_value: str = Field(..., description="字段值")


class AutoFillResponse(BaseModel):
    """自动填充接口响应。"""
    success: bool = True
    matched: bool = Field(..., description="是否匹配到数据")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="外部 API 返回的数据")
    message: Optional[str] = Field(None, description="提示信息")
