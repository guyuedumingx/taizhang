"""
EHR 号格式校验器 (PRD §3.2 + §17.3)
=========================================

要求: 恰好 7 位数字, 前导零不省略.

提供两层校验:
  - validate_ehr_format(value: str) -> str: 普通函数, 校验失败抛 ValueError
  - EhrIdStr: Annotated[str, AfterValidator] Pydantic 类型, 用于 schema 字段

接入点:
  - app.schemas.user.UserCreate.ehr_id (注册/创建)
  - app.schemas.user.UserUpdate.ehr_id (修改, 选填)
  - app.api.api_v1.endpoints.auth.login (登录 username 实为 EHR)
  - app.api.api_v1.endpoints.users.import_users (批量导入)
"""
import re
from typing import Annotated

from fastapi import HTTPException
from pydantic import AfterValidator

from app.core.config import settings

EHR_PATTERN = re.compile(settings.EHR_REGEX)
EHR_LENGTH = 7


def validate_ehr_format(value: str) -> str:
    """校验 EHR 号格式: 恰好 7 位数字. 失败抛 ValueError.

    Pydantic AfterValidator 友好 (ValueError 会被转 422).
    """
    if value is None:
        raise ValueError("EHR号不能为空")
    if not isinstance(value, str):
        raise ValueError("EHR号必须是字符串")
    if len(value) != EHR_LENGTH:
        raise ValueError(f"EHR号必须是 {EHR_LENGTH} 位数字, 当前 {len(value)} 位")
    if not EHR_PATTERN.match(value):
        raise ValueError("EHR号必须仅含数字 (0-9), 前导零不省略")
    return value


def assert_valid_ehr(value: str) -> None:
    """同步函数, 失败抛 HTTPException(400). 用于非 Pydantic 场景 (如批量导入)."""
    try:
        validate_ehr_format(value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"EHR号格式错误: {e}")


# Pydantic 注解类型: 在 schema 字段后用 `Annotated[str, EhrFieldIdAfterValidator]`
EhrIdStr = Annotated[str, AfterValidator(validate_ehr_format)]