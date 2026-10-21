import random
import string


def random_lower_string(length=32):
    """生成随机小写字母字符串"""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_compliant_password(length=12):
    """生成符合密码策略的随机密码 (大写+小写+数字+特殊字符, ≥8 位)

    策略单一来源: app/core/password_validator.py
    (schemas.UserCreate 会用它校验, 弱密码会直接 422)
    """
    if length < 8:
        length = 8
    specials = "!@#$%^&*"
    base = (
        random.choice(string.ascii_uppercase)
        + random.choice(string.ascii_lowercase)
        + random.choice(string.digits)
        + random.choice(specials)
    )
    pool = string.ascii_letters + string.digits + specials
    return base + "".join(random.choices(pool, k=length - 4))


def random_email():
    """生成随机邮箱地址"""
    domain = "example.com"
    username = random_lower_string(8)
    return f"{username}@{domain}" 