from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class TokenPayload(BaseModel):
    sub: Optional[int] = None 