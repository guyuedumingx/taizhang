from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel


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


class PasswordChangeResponse(BaseModel):
    success: bool
    message: str


class PasswordExpiredResponse(BaseModel):
    password_expired: bool
    days_until_expiry: int
    last_password_change: Optional[datetime] = None 