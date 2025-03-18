from typing import Optional, List
from datetime import datetime, timedelta

from pydantic import BaseModel, validator, constr


# 共享属性
class UserBase(BaseModel):
    username: Optional[str] = None
    ehr_id: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    team_id: Optional[int] = None


# 创建用户时的属性
class UserCreate(UserBase):
    username: str
    ehr_id: constr(min_length=7, max_length=7, pattern=r'^\d{7}$')
    password: str
    roles: Optional[List[str]] = None
    
    @validator('ehr_id')
    def ehr_id_must_be_7_digits(cls, v):
        if not v.isdigit() or len(v) != 7:
            raise ValueError('EHR号必须是7位数字')
        return v


# 更新用户时的属性
class UserUpdate(UserBase):
    password: Optional[str] = None
    role: Optional[str] = None


# 数据库中的用户
class UserInDBBase(UserBase):
    id: int
    last_password_change: Optional[datetime] = None

    class Config:
        orm_mode = True


# 返回给API的用户
class User(UserInDBBase):
    roles: Optional[List[str]] = []
    password_expired: Optional[bool] = False

    @validator('password_expired', always=True)
    def check_password_expired(cls, v, values):
        if 'last_password_change' in values and values['last_password_change']:
            # 检查密码是否超过3个月未更改
            three_months_ago = datetime.now() - timedelta(days=90)
            return values['last_password_change'] < three_months_ago
        return False


# 数据库中存储的用户，包含哈希密码
class UserInDB(UserInDBBase):
    hashed_password: str


# 用户导入响应
class UserImportResponse(BaseModel):
    success_count: int
    failed_count: int
    failed_users: List[dict] 