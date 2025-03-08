from typing import Optional, List

from pydantic import BaseModel


# 共享属性
class TeamBase(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    leader_id: Optional[int] = None


# 创建团队时的属性
class TeamCreate(TeamBase):
    name: str
    department: str


# 更新团队时的属性
class TeamUpdate(TeamBase):
    pass


# 数据库中的团队
class TeamInDBBase(TeamBase):
    id: int

    class Config:
        orm_mode = True


# 返回给API的团队
class Team(TeamInDBBase):
    leader_name: Optional[str] = None
    member_count: int = 0 