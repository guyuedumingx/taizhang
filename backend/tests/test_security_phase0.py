"""Phase 0 安全修复验证测试 (重构方案)

覆盖:
  1. 服务端强制改密: 首次登录用户访问业务 API 403, 放行端点可用, 改密后恢复
  2. 密码过期 (90 天) 同样被服务端拦截
  3. 登录失败锁定: 连续 5 次失败 → 429; 成功登录重置计数
  4. 自我提权修复: 普通用户 PUT 自己 {"is_superuser": true} 无效
  5. 改密密码策略: 大写+小写+数字+特殊字符 且 ≥8 位, 否则 422
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.login_throttle import login_throttle
from app.main import app
from app.services.auth_service import auth_service, _set_is_first_login

client = TestClient(app)
API = "/api/v1"


@pytest.fixture(autouse=True)
def _clear_throttle():
    """进程级锁定状态在用例间必须清零, 否则跨用例误锁。"""
    login_throttle._failures.clear()
    yield
    login_throttle._failures.clear()


def _login(ehr_id: str, password: str):
    return client.post(f"{API}/auth/login", data={"username": ehr_id, "password": password})


# ---------------------------------------------------------------- 1. 强制改密
class TestFirstLoginEnforcement:
    def test_first_login_blocks_business_api(self, db: Session, normal_user: models.User):
        _set_is_first_login(db, normal_user.id, True)
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get(f"{API}/users/members", headers=headers)
        assert r.status_code == 403, r.text
        assert "PASSWORD_CHANGE_REQUIRED" in r.json()["detail"]

    def test_first_login_allows_change_password_path(self, db: Session, normal_user: models.User):
        _set_is_first_login(db, normal_user.id, True)
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get(f"{API}/auth/me", headers=headers).status_code == 200
        r = client.post(
            f"{API}/auth/change-password",
            headers=headers,
            json={"current_password": "User123!", "new_password": "NewPass123!"},
        )
        assert r.status_code == 200, r.text

    def test_after_password_change_access_restored(self, db: Session, normal_user: models.User):
        _set_is_first_login(db, normal_user.id, True)
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get(f"{API}/users/members", headers=headers).status_code == 403

        client.post(
            f"{API}/auth/change-password",
            headers=headers,
            json={"current_password": "User123!", "new_password": "NewPass123!"},
        )
        assert client.get(f"{API}/users/members", headers=headers).status_code == 200


# ---------------------------------------------------------------- 2. 密码过期
class TestPasswordExpiryEnforcement:
    def test_expired_password_blocks_api(self, db: Session, normal_user: models.User):
        normal_user.last_password_change = datetime.now() - timedelta(days=100)
        db.commit()
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]

        r = client.get(
            f"{API}/users/members", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 403, r.text
        assert "PASSWORD_EXPIRED" in r.json()["detail"]

    def test_fresh_password_not_blocked(self, db: Session, normal_user: models.User):
        normal_user.last_password_change = datetime.now()
        db.commit()
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert client.get(
            f"{API}/users/members", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 200


# ---------------------------------------------------------------- 3. 登录锁定
class TestLoginThrottle:
    def test_five_failures_then_locked(self, db: Session, normal_user: models.User):
        for _ in range(5):
            assert _login(normal_user.ehr_id, "wrong000").status_code == 401
        r = _login(normal_user.ehr_id, "User123!")  # 即使密码正确也锁
        assert r.status_code == 429, r.text

    def test_success_resets_counter(self, db: Session, normal_user: models.User):
        for _ in range(4):
            _login(normal_user.ehr_id, "wrong000")
        assert _login(normal_user.ehr_id, "User123!").status_code == 200
        # 计数已清零: 再错 4 次仍不应锁
        for _ in range(4):
            _login(normal_user.ehr_id, "wrong000")
        assert _login(normal_user.ehr_id, "User123!").status_code == 200


# ---------------------------------------------------------------- 4. 提权修复
class TestSelfUpdatePrivilegeEscalation:
    def test_normal_user_cannot_grant_superuser(self, db: Session, normal_user: models.User, admin_user: models.User):
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.put(
            f"{API}/users/{normal_user.id}",
            headers=headers,
            json={"is_superuser": True, "roles": ["admin"], "is_active": True},
        )
        # 白名单字段之外的载荷被丢弃 —— 用户更新成功, 但没有提权
        assert r.status_code == 200, r.text
        db.refresh(normal_user)
        assert normal_user.is_superuser is False

    def test_normal_user_cannot_change_own_password_without_old(
        self, db: Session, normal_user: models.User
    ):
        """自助通道剥离 password 字段: 改密必须走验旧密码的 /auth/change-password"""
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        r = client.put(
            f"{API}/users/{normal_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "Strong@123"},
        )
        assert r.status_code == 200, r.text
        # 原密码仍可登录 = password 字段被丢弃
        assert _login(normal_user.ehr_id, "User123!").status_code == 200
        # 且新密码不生效
        assert _login(normal_user.ehr_id, "Strong@123").status_code == 401

    def test_weak_password_rejected_before_permission_strip(
        self, db: Session, normal_user: models.User
    ):
        """弱密码在任何更新通道都 422 (策略在 schema 层, 早于权限剥离)"""
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        r = client.put(
            f"{API}/users/{normal_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "999999"},
        )
        assert r.status_code == 422, r.text

    def test_admin_full_update_still_works(
        self, db: Session, normal_user: models.User, admin_user: models.User
    ):
        token = _login(admin_user.ehr_id, "Admin123!").json()["access_token"]
        r = client.put(
            f"{API}/users/{normal_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"department": "新部门"},
        )
        assert r.status_code == 200, r.text
        db.refresh(normal_user)
        assert normal_user.department == "新部门"


# ---------------------------------------------------------------- 5. 密码策略
class TestPasswordPolicy:
    """策略单一来源: app/core/password_validator.py
    大写 + 小写 + 数字 + 特殊字符, 且 ≥8 位 (2026-10-21 决策: 全局统一)
    """

    def _change(self, token: str, new_password: str):
        return client.post(
            f"{API}/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "User123!", "new_password": new_password},
        )

    def test_short_password_rejected(self, db: Session, normal_user: models.User):
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert self._change(token, "Ab1!").status_code == 422

    def test_digits_only_rejected(self, db: Session, normal_user: models.User):
        """旧规则 (6 位纯数字) 放行的密码, 新规则必须拒绝"""
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert self._change(token, "12345678").status_code == 422

    def test_missing_uppercase_rejected(self, db: Session, normal_user: models.User):
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert self._change(token, "abcdefg1!").status_code == 422

    def test_missing_special_rejected(self, db: Session, normal_user: models.User):
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert self._change(token, "Abcdefg1").status_code == 422

    def test_compliant_password_accepted(self, db: Session, normal_user: models.User):
        token = _login(normal_user.ehr_id, "User123!").json()["access_token"]
        assert self._change(token, "Valid@123").status_code == 200
        # 改密后新密码真的能登录 (不是只返回 200)
        assert _login(normal_user.ehr_id, "Valid@123").status_code == 200
