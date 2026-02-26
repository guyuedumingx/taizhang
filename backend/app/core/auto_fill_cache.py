"""
自动填充 Token 缓存：仅内存存储，key 为 auto_fill:token:{user_id}。
不落库、不提供查询接口；仅当台账用户调用自动填充接口时在内部使用。
"""
from datetime import datetime, timedelta
from typing import Optional

# 内存缓存：key -> (token_value, expires_at)
_auto_fill_token_cache: dict[str, tuple[str, datetime]] = {}
# 默认 TTL（秒），可配置；0 表示不过期
AUTO_FILL_TOKEN_CACHE_TTL_SECONDS = 86400  # 24 小时


def _cache_key(user_id: str) -> str:
    return f"auto_fill:token:{user_id}"


def get_auto_fill_token(user_id: str, ttl_seconds: int = AUTO_FILL_TOKEN_CACHE_TTL_SECONDS) -> Optional[str]:
    """
    从缓存获取指定用户的 Token。若已过期则删除并返回 None。
    """
    key = _cache_key(user_id)
    if key not in _auto_fill_token_cache:
        return None
    token_value, expires_at = _auto_fill_token_cache[key]
    if ttl_seconds > 0 and datetime.now() >= expires_at:
        del _auto_fill_token_cache[key]
        return None
    return token_value


def set_auto_fill_token(
    user_id: str,
    token: str,
    ttl_seconds: int = AUTO_FILL_TOKEN_CACHE_TTL_SECONDS,
) -> None:
    """
    将用户号与 Token 写入缓存。相同 user_id 会覆盖。
    """
    key = _cache_key(user_id)
    expires_at = datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds > 0 else datetime.max
    _auto_fill_token_cache[key] = (token, expires_at)
