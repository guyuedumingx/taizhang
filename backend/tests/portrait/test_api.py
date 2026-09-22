"""
portrait 后端 MVP 测试 (P5 阶段, 批次 8)

覆盖 (15 test):
  - health + permissions 基线 (4 test)
  - Profile 查改 + 权限隔离 (5 test)
  - Submission 创建 (4 test)
  - 审批状态机 + 边界 (3 test, 含 Rule 12 显性化)

复用 tests/conftest.py 已有 fixtures (db / admin_user / normal_user / *_token_headers),
不依赖 workflow_instance 等未定义 fixture.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.main import app


client = TestClient(app)

API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


# ============================================================================
# 健康 + 权限基线 (4 test)
# ============================================================================
def test_health_no_auth():
    """GET /portrait/health 不需要 token"""
    response = client.get(f"{API_PORTRAIT}/health")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "portrait"


def test_me_permissions_admin(admin_token_headers: dict):
    """admin /me/permissions 拿到 portrait_all + portrait_self + portrait_group"""
    response = client.get(f"{API_PORTRAIT}/me/permissions", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_admin"] is True
    assert data["is_leader"] is False
    perms = data["permissions"]
    assert "*" in perms["portrait_all"]
    assert "read" in perms["portrait_self"]
    assert "update" in perms["portrait_self"]


def test_me_permissions_user(normal_token_headers: dict, normal_user: models.User):
    """普通 user /me/permissions: 无 portrait_all, 有 portrait_self"""
    response = client.get(f"{API_PORTRAIT}/me/permissions", headers=normal_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_admin"] is False
    assert data["is_user"] is True
    perms = data["permissions"]
    # 普通用户无 admin 通配
    assert perms["portrait_all"] == []
    # portrait_self 永远有 (前端 hasPermission 自己用)
    assert "read" in perms["portrait_self"]


def test_me_permissions_requires_auth():
    """无 token /me/permissions 必须 401"""
    response = client.get(f"{API_PORTRAIT}/me/permissions")
    assert response.status_code == 401


# ============================================================================
# Profile 查改 (5 test)
# ============================================================================
def test_profiles_me_returns_user_info(admin_token_headers: dict, admin_user: models.User):
    """GET /portrait/profiles/me 返回 user_name + ehr_id + 9 子表"""
    response = client.get(f"{API_PORTRAIT}/profiles/me", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user_name"] == admin_user.name
    assert data["ehr_id"] == admin_user.ehr_id
    assert data["department"] == admin_user.department
    # 9 子表全部存在 (可以是 null)
    for sub in [
        "political", "education", "family", "resume", "reward",
        "qualification", "achievement", "language", "contact",
    ]:
        assert sub in data, f"missing subtable: {sub}"


def test_profiles_me_update_partial_fields(
    admin_token_headers: dict, db: Session, admin_user: models.User
):
    """PUT /portrait/profiles/me 改非受保护字段 (gender / nation) 成功"""
    update = {"gender": "male", "nation": "汉族"}
    response = client.put(
        f"{API_PORTRAIT}/profiles/me", headers=admin_token_headers, json=update
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["gender"] == "male"
    assert data["nation"] == "汉族"


def test_profiles_me_update_protected_field_ignored(
    admin_token_headers: dict, db: Session, admin_user: models.User
):
    """PUT /profiles/me 发受保护字段 id_type → schema extra=ignore 静默丢弃, profile.id_type 不变

    设计: ProfileUpdate 不暴露 id_type / id_number / is_emergency_staff (Pydantic v2 默认 extra=ignore),
    service.model_dump(exclude_unset=True) 也不会拿到这些字段. 受保护字段必须走 profile_edit 审批流.

    Rule 9: 测试验证有意义的属性 — 此处验证"发受保护字段不会污染 profile".
    """
    # 先记下原 id_type (可能为 null)
    before_resp = client.get(
        f"{API_PORTRAIT}/profiles/me", headers=admin_token_headers
    )
    before_id_type = before_resp.json().get("id_type")

    # 发受保护字段
    update = {"id_type": "护照", "is_emergency_staff": True, "gender": "male"}
    response = client.put(
        f"{API_PORTRAIT}/profiles/me", headers=admin_token_headers, json=update
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # gender 被更新 (合法字段)
    assert data["gender"] == "male"
    # 受保护字段 id_type / is_emergency_staff 未变
    assert data["id_type"] == before_id_type
    assert data["is_emergency_staff"] is False


def test_profiles_list_admin_sees_all(admin_token_headers: dict):
    """admin /profiles 看到分页结果 (List 不要求一定非空, 跑过就行)"""
    response = client.get(f"{API_PORTRAIT}/profiles", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_profiles_list_user_sees_self_only(
    normal_token_headers: dict, normal_user: models.User
):
    """普通 user /profiles 只看到自己 (service 层 _can_view_profile 过滤)"""
    response = client.get(f"{API_PORTRAIT}/profiles", headers=normal_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    # 普通 user 只能看到自己的 profile
    # 由于 profile 可能尚未创建, 看到 0 个是合理的; 如果已存在也只能 1 个
    assert data["total"] <= 1


def test_profiles_list_403_for_other_user(
    normal_token_headers: dict, admin_user: models.User
):
    """普通 user 查 admin 的 ehr_id 应 403 (无权跨用户)"""
    response = client.get(
        f"{API_PORTRAIT}/profiles/{admin_user.ehr_id}", headers=normal_token_headers
    )
    assert response.status_code == 403, response.text


# ============================================================================
# Submission 创建 (4 test)
# ============================================================================
def test_create_submission_special_work(
    normal_token_headers: dict, admin_user: models.User, normal_user: models.User
):
    """创建 special_work 提交, 必须 next_approver_id 指定"""
    payload = {
        "submission_type": "special_work",
        "payload": {
            "project_name": "测试专项工作",
            "start_time": "2026-01-01",
            "content": "测试内容",
            "hours": 8,
        },
        "next_approver_id": admin_user.id,
    }
    response = client.post(
        f"{API_PORTRAIT}/submissions", headers=normal_token_headers, json=payload
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["submission_type"] == "special_work"
    assert data["status"] == "pending"
    assert data["current_approver_id"] == admin_user.id


def test_create_submission_skill_tag_edit_admin(
    normal_token_headers: dict, admin_user: models.User
):
    """创建 skill_tag_edit 提交, 不指定 next_approver_id 时自动找 admin"""
    payload = {
        "submission_type": "skill_tag_edit",
        "payload": {
            "tag_name": "测试亮点",
            "action": "add",
            "sensitivity": "low",
        },
    }
    response = client.post(
        f"{API_PORTRAIT}/submissions", headers=normal_token_headers, json=payload
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["submission_type"] == "skill_tag_edit"
    # 自动找到 admin (第一个 is_superuser=True)
    assert data["current_approver_id"] == admin_user.id


def test_create_submission_invalid_payload_400(normal_token_headers: dict):
    """payload 缺字段 → 400 (集成指南 Rule 12 显性化)"""
    payload = {
        "submission_type": "special_work",
        "payload": {"project_name": "缺 start_time / content / hours"},
    }
    response = client.post(
        f"{API_PORTRAIT}/submissions", headers=normal_token_headers, json=payload
    )
    assert response.status_code == 400, response.text
    assert "缺少字段" in response.text


def test_create_submission_invalid_type_400(normal_token_headers: dict):
    """submission_type 非法 → 422 (Pydantic pattern 拒绝)"""
    payload = {
        "submission_type": "invalid_type",
        "payload": {"foo": "bar"},
    }
    response = client.post(
        f"{API_PORTRAIT}/submissions", headers=normal_token_headers, json=payload
    )
    # Pydantic v2 pattern 校验失败 → 422
    assert response.status_code == 422, response.text


# ============================================================================
# 审批状态机 (3 test)
# ============================================================================
def _create_pending_for_admin(
    normal_token_headers: dict, admin_user: models.User
) -> int:
    """helper: 给 admin 创建一个 pending 提交, 返回 id"""
    payload = {
        "submission_type": "special_work",
        "payload": {
            "project_name": "待审批的提交",
            "start_time": "2026-01-01",
            "content": "test",
            "hours": 4,
        },
        "next_approver_id": admin_user.id,
    }
    response = client.post(
        f"{API_PORTRAIT}/submissions", headers=normal_token_headers, json=payload
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_approve_pending_to_approved(
    normal_token_headers: dict,
    admin_token_headers: dict,
    admin_user: models.User,
):
    """admin 审批通过 pending 提交 → status=approved"""
    sub_id = _create_pending_for_admin(normal_token_headers, admin_user)
    response = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "OK"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["submission"]["status"] == "approved"


def test_approve_rejects_empty_comment(
    normal_token_headers: dict,
    admin_token_headers: dict,
    admin_user: models.User,
):
    """reject 空 comment → 400 (Rule 12 显性化, 不吞错)"""
    sub_id = _create_pending_for_admin(normal_token_headers, admin_user)
    # 空字符串
    response = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/reject",
        headers=admin_token_headers,
        json={"comment": ""},
    )
    assert response.status_code == 400, response.text
    assert "驳回必须填写意见" in response.text
    # 全空白
    response = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/reject",
        headers=admin_token_headers,
        json={"comment": "   "},
    )
    assert response.status_code == 400, response.text


def test_approve_rejects_non_approver(
    normal_token_headers: dict,
    admin_token_headers: dict,
    admin_user: models.User,
):
    """非审批人 approve → 403 (service 层 _ensure_can_act 拒绝)"""
    sub_id = _create_pending_for_admin(normal_token_headers, admin_user)
    # normal_user 不是 current_approver (admin 才是), 也不是 superuser → 403
    response = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=normal_token_headers,
        json={"comment": "我抢批"},
    )
    assert response.status_code == 403, response.text


def test_withdraw_only_submitter_pending(
    normal_token_headers: dict,
    admin_token_headers: dict,
    admin_user: models.User,
):
    """submitter 本人撤回 pending → status=cancelled; admin 撤回他人 → 403"""
    sub_id = _create_pending_for_admin(normal_token_headers, admin_user)
    # normal_user 自己撤回
    response = client.delete(
        f"{API_PORTRAIT}/submissions/{sub_id}", headers=normal_token_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"

    # 再建一个, admin 试图撤回别人的提交
    sub_id2 = _create_pending_for_admin(normal_token_headers, admin_user)
    response = client.delete(
        f"{API_PORTRAIT}/submissions/{sub_id2}", headers=admin_token_headers
    )
    assert response.status_code == 403, response.text
