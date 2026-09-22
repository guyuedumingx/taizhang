"""
portrait 共享 schema (分页 / 错误响应 / 提交动作)

集成指南 §3 阶段 4: portrait P4 后端 API MVP
"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应 (抄 app/schemas/common.py PaginatedResponse 风格)"""
    items: List[T]
    total: int
    page: int
    size: int


class ErrorResponse(BaseModel):
    """统一错误响应 (集成指南 §5 雷区合规: 错误显性化, Rule 12)"""
    detail: str
    code: Optional[str] = None