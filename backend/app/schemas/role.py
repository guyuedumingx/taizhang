from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel


# 共享属性
class RoleBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_system: bool = False


# 创建角色时的属性
class RoleCreate(RoleBase):
    name: str
    permissions: List[str] = []


# 更新角色时的属性
class RoleUpdate(RoleBase):
    permissions: Optional[List[str]] = None


# 数据库中的角色
class RoleInDBBase(RoleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 返回给API的角色
class Role(RoleInDBBase):
    permissions: List[str] = [] 