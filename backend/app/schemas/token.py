from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.password_validator import validate_password_strength


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    name: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    teamId: Optional[int] = None
    password_expired: bool = False


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    roles: List[str] = []


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    # 2026-10-21 决策: 密码策略全局统一为「大小写 + 数字 + 特殊字符, ≥8 位」
    # (决策 2 的导入规则)。此前这里是"至少 6 位纯数字", 与导入端相反 ——
    # 管理员在 Excel 里填强密码, 员工首登强制改密时却被要求改成 123456,
    # 安全强度在改密这一步被反向击穿。
    #
    # 只校验**新密码**, 不校验旧密码: 存量用户的 6 位纯数字密码仍能登录,
    # 但改密时必须设成强密码 (这正是要的效果)。
    @field_validator("new_password")
    @classmethod
    def _new_password_policy(cls, v: str) -> str:
        return validate_password_strength(v, label="新密码")


class PasswordChangeResponse(BaseModel):
    success: bool
    message: str


class PasswordExpiredResponse(BaseModel):
    password_expired: bool
    days_until_expiry: int
    last_password_change: Optional[datetime] = None 