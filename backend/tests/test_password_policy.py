"""全局密码策略验证 (2026-10-21 决策: 全局统一为 大写+小写+数字+特殊字符, ≥8 位)

策略单一来源: app/core/password_validator.py
本文件锁定"所有入口都走同一条规则", 防止将来某个入口漏校验或口径漂移。
"""
import pytest
from pydantic import ValidationError

from app.core.password_validator import validate_password_strength
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.token import PasswordChange

# 每条策略各缺一项的样本 —— 逐条必须被拒
WEAK_PASSWORDS = [
    "abcdefgh",      # 缺大写 / 缺数字 / 缺特殊字符
    "ABCDEFGH",      # 缺小写 / 缺数字 / 缺特殊字符
    "12345678",      # 缺大写 / 缺小写 / 缺特殊字符 (旧规则放行)
    "Abcdefgh",      # 缺数字 / 缺特殊字符
    "Abcdefg1",      # 缺特殊字符
    "Abc1!23",       # 长度 7, 不足 8
    "Ab1!",          # 长度 4
]

COMPLIANT_PASSWORD = "Valid@123"


class TestValidator:
    """validate_password_strength 本身的语义"""

    @pytest.mark.parametrize("password", WEAK_PASSWORDS)
    def test_weak_rejected(self, password: str):
        with pytest.raises(ValueError):
            validate_password_strength(password)

    def test_compliant_accepted(self):
        assert validate_password_strength(COMPLIANT_PASSWORD) == COMPLIANT_PASSWORD

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            validate_password_strength("")

    def test_error_message_lists_missing_items(self):
        """错误信息要说清缺什么, 而不是笼统的 'invalid password'"""
        with pytest.raises(ValueError) as excinfo:
            validate_password_strength("abcdefgh", label="初始密码")
        msg = str(excinfo.value)
        assert "初始密码" in msg
        assert "大写字母" in msg
        assert "数字" in msg
        assert "特殊字符" in msg


class TestUserCreate:
    def test_weak_rejected(self):
        for password in WEAK_PASSWORDS:
            with pytest.raises(ValidationError):
                UserCreate(
                    username="u",
                    ehr_id="1234567",
                    name="测试",
                    password=password,
                )

    def test_compliant_accepted(self):
        user = UserCreate(
            username="u",
            ehr_id="1234567",
            name="测试",
            password=COMPLIANT_PASSWORD,
        )
        assert user.password == COMPLIANT_PASSWORD


class TestUserUpdate:
    def test_weak_rejected(self):
        with pytest.raises(ValidationError):
            UserUpdate(password="12345678")

    def test_none_password_allowed(self):
        """不传密码 = 不改密码, 不能因为 None 被拒"""
        assert UserUpdate(department="新部门").password is None

    def test_empty_password_allowed(self):
        """空串在前端等于"留空不改", 不能被拒"""
        assert UserUpdate(password="").password == ""


class TestPasswordChange:
    def test_weak_rejected(self):
        for password in WEAK_PASSWORDS:
            with pytest.raises(ValidationError):
                PasswordChange(current_password="Old@12345", new_password=password)

    def test_compliant_accepted(self):
        data = PasswordChange(
            current_password="Old@12345", new_password=COMPLIANT_PASSWORD
        )
        assert data.new_password == COMPLIANT_PASSWORD


def test_schema_entrypoints_share_one_implementation():
    """UserCreate / UserUpdate / PasswordChange 必须引用同一个校验器 (防口径漂移)"""
    import app.schemas.user as user_schema
    import app.schemas.token as token_schema

    assert user_schema.validate_password_strength is validate_password_strength
    assert token_schema.validate_password_strength is validate_password_strength
