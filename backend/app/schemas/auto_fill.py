"""自动填充相关 Schema：接收 Token、自动填充请求/响应。"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AutoFillTokenReceive(BaseModel):
    """接收并缓存 Token 的请求体。"""
    user_id: str = Field(..., description="用户号（台账系统用户标识或可与台账用户关联的标识）")
    token: str = Field(..., description="外部系统的访问 Token")


class AutoFillTokenResponse(BaseModel):
    """接收 Token 接口的响应。"""
    success: bool = True
    message: str = "Token已接收并缓存"


class AutoFillRequest(BaseModel):
    """自动填充接口请求体。"""
    field_name: str = Field(..., description="触发匹配的字段名")
    field_value: str = Field(..., description="字段值")


class AutoFillSource(BaseModel):
    """自动填充数据来源说明。"""
    system_name: str = Field(..., description="外部系统名称")
    external_id: Optional[str] = Field(None, description="外部系统中的记录 ID")


class AutoFillResponse(BaseModel):
    """自动填充接口响应（匹配成功时含 raw_data）。"""
    success: bool = True
    matched: bool = Field(..., description="是否匹配到数据")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="外部系统返回的原始数据（仅 matched 时存在）")
    source: Optional[AutoFillSource] = Field(None, description="数据来源（仅 matched 时存在）")
    message: Optional[str] = Field(None, description="未匹配或提示信息")
