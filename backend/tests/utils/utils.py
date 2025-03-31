import random
import string


def random_lower_string(length=32):
    """生成随机小写字母字符串"""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email():
    """生成随机邮箱地址"""
    domain = "example.com"
    username = random_lower_string(8)
    return f"{username}@{domain}" 