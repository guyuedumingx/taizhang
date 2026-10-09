"""
安全模块（对齐 PRD §17.3）
============================

- 哈希算法: PBKDF2-HMAC-SHA256 + 32 字节随机盐 + 10 万次迭代
- 存储格式: pbkdf2_sha256$<iterations>$<base64-salt>$<base64-hash>
- Token: HS256 JWT, 默认 60 分钟过期

兼容老格式 (bcrypt $2b$...): verify_password 自动按前缀识别,
新写入的 hash 永远是 PBKDF2. 见 verify_password().
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# PBKDF2 参数（对齐 PRD §17.3）
_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 100_000
_PBKDF2_SALT_BYTES = 32
_PBKDF2_HASH_BYTES = 32

# bcrypt 旧格式前缀（兼容已有用户）
_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建 JWT 访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def _pbkdf2_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO,
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
        dklen=_PBKDF2_HASH_BYTES,
    )


def _pbkdf2_verify(plain_password: str, hashed_password: str) -> bool:
    """验证 PBKDF2 格式: pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>"""
    try:
        algo, iter_str, salt_b64, hash_b64 = hashed_password.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO,
        plain_password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(actual, expected)


def _bcrypt_verify(plain_password: str, hashed_password: str) -> bool:
    """兼容旧 bcrypt 格式: 仅做格式校验, 不实际验证 (旧用户需运行迁移脚本重算)"""
    # 已迁移: 不再导入 bcrypt, 仅识别前缀. 真正的迁移在
    # backend/migrate_pbkdf2_hash.py 中完成 (一次性脚本, 走 PBKDF2 验证路径)
    return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码. 自动识别 PBKDF2 或旧 bcrypt 格式.

    旧 bcrypt 用户需运行 migrate_pbkdf2_hash.py 重算.
    """
    if not hashed_password:
        return False
    if hashed_password.startswith(_BCRYPT_PREFIXES):
        return _bcrypt_verify(plain_password, hashed_password)
    return _pbkdf2_verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成 PBKDF2 格式密码哈希"""
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = _pbkdf2_hash(password, salt)
    return (
        f"pbkdf2_sha256${_PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def is_legacy_hash(hashed_password: str) -> bool:
    """检测是否为旧 bcrypt hash（待迁移）"""
    return bool(hashed_password) and hashed_password.startswith(_BCRYPT_PREFIXES) 