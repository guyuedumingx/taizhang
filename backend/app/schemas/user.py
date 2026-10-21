from typing import Optional, List
from datetime import datetime, timedelta

from pydantic import BaseModel, validator

from app.core.ehr_validator import EhrIdStr
from app.core.password_validator import validate_password_strength


# 共享属性
class UserBase(BaseModel):
    username: Optional[str] = None
    ehr_id: Optional[EhrIdStr] = None  # PRD §3.2: 恰好 7 位数字
    name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    team_id: Optional[int] = None


# 创建用户时的属性
class UserCreate(UserBase):
    username: str
    ehr_id: EhrIdStr  # 创建时必填, 自动校验 7 位数字
    password: str
    name: str
    roles: Optional[List[str]] = None

    # 2026-10-21 决策: 密码策略全局统一 (见 app/core/password_validator.py)。
    # 此前建号接口对密码**零校验**, 前端只要求"至少 6 个字符" —— 管理员可以
    # 建出 6 位纯数字的账号, 与 Excel 导入端的复杂度要求自相矛盾。
    @validator("password")
    def _password_policy(cls, v: str) -> str:
        return validate_password_strength(v, label="密码")


# 更新用户时的属性
class UserUpdate(UserBase):
    password: Optional[str] = None
    roles: Optional[list[str]] = None

    # 管理员重置密码走同一条规则 (传了才校验, 不传=不改密码)
    @validator("password")
    def _password_policy(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_password_strength(v, label="新密码")


# 自助更新白名单 (Phase 0: 评审 P0-3)。
# PUT /users/{自己的id} 无需 user:edit 权限, 此前直接复用 UserUpdate —— 继承了
# is_superuser / is_active / team_id, 还带 password / roles, 任意登录用户可
# {"is_superuser": true} 自我提权。自助通道只允许改这三个字段; 敏感字段与
# 改密 (走 /auth/change-password, 验旧密码) 一律不在此列。
class UserSelfUpdate(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None


# 数据库中的用户
class UserInDBBase(UserBase):
    id: int
    last_password_change: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


# 返回给API的用户
class User(UserInDBBase):
    roles: Optional[List[str]] = []
    password_expired: Optional[bool] = False
    is_first_login: Optional[bool] = None  # PRD §3.2: 首次登录标志
    # 安全: hashed_password 绝不能出现在对外响应 schema 里。
    # 它曾被放在此处, 导致 GET /api/v1/users/ 向任意登录用户吐出全行 1494 人的
    # 密码哈希 (PBKDF2) + username, 可离线定向爆破。内部需要时用下面的 UserInDB。

    @validator('password_expired', always=True)
    def check_password_expired(cls, v, values):
        if 'last_password_change' in values and values['last_password_change']:
            # 检查密码是否超过3个月未更改
            three_months_ago = datetime.now() - timedelta(days=90)
            return values['last_password_change'] < three_months_ago
        return False

    class Config:
        orm_mode = True
        from_attributes = True


# 员工通讯录最小集: 供家访登记 / 工作流审批人选择这类业务选择器使用。
# 与 User 的区别是**不暴露** department / roles / is_superuser / team_id,
# 避免任意登录员工通过业务页面的下拉框拿到全行组织架构与管理员名单。
class UserMember(BaseModel):
    id: int
    username: Optional[str] = None
    name: Optional[str] = None
    ehr_id: Optional[EhrIdStr] = None
    # team_id 保留: 家访登记用它把"被家访人"下拉框限定在本团队,
    # 而不是列出全行 1494 人。团队归属是员工自己能看到的公开信息。
    team_id: Optional[int] = None

    class Config:
        from_attributes = True


# 数据库中存储的用户，包含哈希密码
class UserInDB(UserInDBBase):
    hashed_password: str


# 用户导入响应
class UserImportResponse(BaseModel):
    success_count: int
    failed_count: int
    failed_users: List[dict] 