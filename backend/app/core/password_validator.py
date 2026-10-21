"""
密码强度校验 (2026-10-16 决策 2; 2026-10-21 全局统一)

规则由业务方给定, 四类字符缺一不可:
  - 必须含大写字母 (A-Z)
  - 必须含小写字母 (a-z)
  - 必须含数字 (0-9)
  - 必须含特殊字符 (非字母数字, 如 ! @ # $ % ^ & *)
  - 长度 >= 8

**全局唯一口径** (2026-10-21 决策: "都搞成大小写+数字+特殊字符≥8 位")。
本文件是这套规则的**唯一实现**, 所有设密码的入口都调它:
  - 管理员建号 / 重置密码  → app/schemas/user.py (UserCreate / UserUpdate)
  - 员工自助改密          → app/schemas/token.py (PasswordChange)
  - Excel 批量导入        → app/api/api_v1/endpoints/users.py (导入端点)

此前改密接口要求的是"至少 6 位纯数字", 与导入端的复杂度规则相反 ——
管理员在 Excel 里填 `Ab3#efGh9`, 员工首登被强制改密时却被要求改成 `123456`,
安全强度在改密这一步被反向击穿。现已统一。

与 ehr_validator 同目录同风格: 校验失败抛 ValueError, 由调用方转成
"整行失败 + 明细" (Rule 12: 不静默降级为弱密码)。
"""
import re

# 特殊字符: 任何非字母非数字非空白字符
_SPECIAL = re.compile(r"[^A-Za-z0-9\s]")
_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"[0-9]")

MIN_LENGTH = 8

# 顺序即明细里的展示顺序, 与业务方给规则的顺序一致
_RULES = [
    ("大写字母", _UPPER),
    ("小写字母", _LOWER),
    ("数字", _DIGIT),
    ("特殊字符", _SPECIAL),
]


def validate_password_strength(password: str, label: str = "密码") -> str:
    """校验密码强度, 通过则原样返回; 不通过抛 ValueError

    Args:
        password: 待校验的明文密码
        label: 报错消息里的密码称呼 (如 "初始密码" / "新密码"), 让用户
            知道是哪一步被拒, 而不是笼统一句"密码不合规"

    Returns:
        原样的 password (便于链式使用)

    Raises:
        ValueError: 缺失任一类字符或长度不足, 消息里列出**全部**缺失项,
            而不是只报第一个 —— 用户一次改对, 不用来回试
    """
    if password is None or not isinstance(password, str) or password == "":
        raise ValueError(f"{label}为空")

    missing = [name for name, pattern in _RULES if not pattern.search(password)]
    if len(password) < MIN_LENGTH:
        missing.append(f"长度≥{MIN_LENGTH}位 (当前 {len(password)} 位)")

    if missing:
        raise ValueError(
            f"{label}不合规, 缺: " + "、".join(missing)
        )
    return password
