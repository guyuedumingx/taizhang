from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, field_validator


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

    # Phase 0 (评审 P1-6): 后端密码策略。与前端 PasswordExpiredModal 规则一致
    # (PRD §3.2 基线): 至少 6 位纯数字。此前后端零校验, 直接调 API 连 6 位
    # 都不要求 —— 前端规则是唯一防线。强度提升另行立项, 本阶段先做到前后端一致。
    @field_validator("new_password")
    @classmethod
    def _new_password_policy(cls, v: str) -> str:
        if len(v) < 6 or not v.isdigit():
            raise ValueError("新密码必须为至少6位数字")
        return v


class PasswordChangeResponse(BaseModel):
    success: bool
    message: str


class PasswordExpiredResponse(BaseModel):
    password_expired: bool
    days_until_expiry: int
    last_password_change: Optional[datetime] = None 