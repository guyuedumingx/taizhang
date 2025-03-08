from typing import Optional, List

from pydantic import BaseModel, EmailStr


# 共享属性
class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    team_id: Optional[int] = None


# 创建用户时的属性
class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str


# 更新用户时的属性
class UserUpdate(UserBase):
    password: Optional[str] = None


# 数据库中的用户
class UserInDBBase(UserBase):
    id: int

    class Config:
        orm_mode = True


# 返回给API的用户
class User(UserInDBBase):
    pass


# 数据库中存储的用户，包含哈希密码
class UserInDB(UserInDBBase):
    hashed_password: str 