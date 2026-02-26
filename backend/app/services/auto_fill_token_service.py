"""
自动填充 Token 解析：先当前用户 Token，无则备用用户 Token。
仅内部使用，不对外暴露 Token。
"""
from typing import Optional

from app.core.config import settings
from app.core.auto_fill_cache import get_auto_fill_token


def get_token_for_auto_fill(current_user_id: str) -> Optional[str]:
    """
    从缓存获取用于调用外部系统的 Token。
    先查当前用户对应的 Token，若无则查配置的备用用户（backup_token_user_id）的 Token。
    current_user_id 应与「接收 Token 接口」写入时的 user_id 一致（如台账用户 ID 的字符串形式）。
    """
    token = get_auto_fill_token(current_user_id)
    if token:
        return token
    config = settings.get_auto_fill_external_system_config()
    if not config:
        return None
    backup_user_id = config.get("backup_token_user_id")
    if backup_user_id:
        return get_auto_fill_token(backup_user_id)
    return None
