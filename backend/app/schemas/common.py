from typing import TypeVar, Generic, List, Any
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class PaginatedResponse(GenericModel, Generic[T]):
    """通用分页响应"""
    items: List[T]
    total: int
    page: int
    size: int 