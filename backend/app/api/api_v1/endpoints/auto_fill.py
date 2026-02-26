"""
自动填充相关接口：接收 Token（仅写入缓存，无查询/直接访问）、模板自动填充（见模块 4）。
"""
from fastapi import APIRouter, HTTPException, status

from app.core.auto_fill_cache import set_auto_fill_token
from app.schemas.auto_fill import AutoFillTokenReceive, AutoFillTokenResponse

router = APIRouter()


@router.post("/token", response_model=AutoFillTokenResponse)
def receive_auto_fill_token(payload: AutoFillTokenReceive) -> AutoFillTokenResponse:
    """
    接收并缓存外部系统 Token。将 user_id 与 token 写入缓存，不落库。
    不提供 GET/查询接口；仅当台账用户调用自动填充接口时在内部从缓存取 Token 使用。
    """
    if not payload.user_id or not payload.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id 与 token 不能为空",
        )
    set_auto_fill_token(payload.user_id, payload.token)
    return AutoFillTokenResponse(success=True, message="Token已接收并缓存")
