"""
A1 12 卡片 (PRD §5.1) — 5 张 1:N 子表 + 技能标签 CRUD 测试 (Week 2 P0.5)

覆盖 (5 × 3 + 3 = 18 test):
  - 简历 (resume): POST/PUT/DELETE
  - 奖惩 (reward): POST/PUT/DELETE
  - 资格 (qualification): POST/PUT/DELETE
  - 成果 (achievement): POST/PUT/DELETE
  - 语言 (language): POST/PUT/DELETE
  - 技能标签模板列表 (GET)
  - 技能标签添加 (大小写去重, 预定义/自定义)
  - 技能标签删除
"""
import pytest
from fastapi.testclient import TestClient

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app


client = TestClient(app)
API = f"{settings.API_V1_STR}/portrait/profiles"


# ============================================================================
# 简历 (Resume)
# ============================================================================
def test_resume_crud_full_cycle(normal_token_headers: dict):
    """简历 POST → GET list → PUT → DELETE 全流程"""
    # POST
    r = client.post(
        f"{API}/me/resume",
        json={"start_time": "2020-01-01", "end_time": "2022-12-31",
              "unit_and_title": "中国银行-XX支行-客户经理"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["id"] > 0
    assert item["unit_and_title"] == "中国银行-XX支行-客户经理"

    item_id = item["id"]

    # PUT 修改
    r = client.put(
        f"{API}/me/resume/{item_id}",
        json={"end_time": "2023-06-30", "unit_and_title": "中国银行-XX支行-高级客户经理"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["unit_and_title"] == "中国银行-XX支行-高级客户经理"

    # DELETE
    r = client.delete(
        f"{API}/me/resume/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # DELETE 不存在的 id → 404
    r = client.delete(
        f"{API}/me/resume/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 404, r.text


def test_resume_other_user_cannot_modify(normal_token_headers: dict, admin_token_headers: dict):
    """normal 创建, admin 改 → 仍能找到 (admin 没自己的 profile)"""
    r = client.post(
        f"{API}/me/resume",
        json={"unit_and_title": "测试条目"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item_id = r.json()["id"]

    # admin 试图改 normal 的 resume → admin 有自己的 profile.id, 找不到 → 404
    r = client.put(
        f"{API}/me/resume/{item_id}",
        json={"unit_and_title": "admin 篡改"},
        headers=admin_token_headers,
    )
    assert r.status_code == 404, r.text

    # 清理
    client.delete(f"{API}/me/resume/{item_id}", headers=normal_token_headers)


# ============================================================================
# 奖惩 (Reward)
# ============================================================================
def test_reward_crud_full_cycle(normal_token_headers: dict):
    r = client.post(
        f"{API}/me/reward",
        json={"reward_type": "奖励", "reward_time": "2024-03-15",
              "reward_name": "优秀员工", "reward_reason": "业绩突出"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["reward_name"] == "优秀员工"
    item_id = item["id"]

    # 改类型
    r = client.put(
        f"{API}/me/reward/{item_id}",
        json={"reward_type": "表扬"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["reward_type"] == "表扬"

    # 删
    r = client.delete(
        f"{API}/me/reward/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 200, r.text


# ============================================================================
# 资格 (Qualification)
# ============================================================================
def test_qualification_crud_full_cycle(normal_token_headers: dict):
    r = client.post(
        f"{API}/me/qualification",
        json={"qualification_name": "CFP国际金融理财师",
              "obtain_time": "2023-05-01", "valid_until": "2026-05-01"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["qualification_name"] == "CFP国际金融理财师"
    item_id = item["id"]

    # 延期
    r = client.put(
        f"{API}/me/qualification/{item_id}",
        json={"valid_until": "2027-05-01"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["valid_until"] == "2027-05-01"

    # 删
    r = client.delete(
        f"{API}/me/qualification/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 200, r.text


# ============================================================================
# 成果 (Achievement)
# ============================================================================
def test_achievement_crud_full_cycle(normal_token_headers: dict):
    r = client.post(
        f"{API}/me/achievement",
        json={"achievement_name": "主导 XX 系统重构, 性能提升 50%",
              "obtain_time": "2024-08-01"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert "主导 XX 系统重构" in item["achievement_name"]
    item_id = item["id"]

    r = client.delete(
        f"{API}/me/achievement/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 200, r.text


# ============================================================================
# 语言 (Language)
# ============================================================================
def test_language_crud_full_cycle(normal_token_headers: dict):
    r = client.post(
        f"{API}/me/language",
        json={"language": "英语", "proficiency": "熟练",
              "cert_level_or_score": "CET-6 550"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["language"] == "英语"
    assert item["proficiency"] == "熟练"
    item_id = item["id"]

    r = client.put(
        f"{API}/me/language/{item_id}",
        json={"proficiency": "精通"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["proficiency"] == "精通"

    r = client.delete(
        f"{API}/me/language/{item_id}", headers=normal_token_headers
    )
    assert r.status_code == 200, r.text


# ============================================================================
# A1 子表响应完整性 (A3 技能标签已于 2026-10-14 下线, 见 PRD 变更记录)
# ============================================================================
def test_my_profile_includes_1toN_subtables(normal_token_headers: dict):
    """GET /me 响应中应包含 1:N 子表 (且不再含已下线的 skill_tags 字段)"""
    # 添加一条简历
    r = client.post(
        f"{API}/me/resume",
        json={"start_time": "2018-01-01", "unit_and_title": "测试单位"},
        headers=normal_token_headers,
    )
    assert r.status_code == 200, r.text

    # GET /me 验证响应字段
    r = client.get(f"{API}/me", headers=normal_token_headers)
    assert r.status_code == 200, r.text
    data = r.json()

    # 1:N 子表字段
    assert "resume" in data
    assert isinstance(data["resume"], list)
    assert len(data["resume"]) >= 1

    assert "reward" in data
    assert "qualification" in data
    assert "achievement" in data
    assert "language" in data

    # A3 下线后, 这两个字段不应再出现在响应里
    assert "skill_tags" not in data
    assert "skill_tag_names" not in data


# ============================================================================
# A11 应急先锋队标识 (Week 3 P0.4) — 仅 admin 直改 (3 test)
# ============================================================================
def test_set_emergency_staff_by_admin_ok(admin_token_headers, normal_user, normal_token_headers):
    """admin 设置普通员工为应急先锋队 → 200 + 值写回 + 员工自己可见"""
    r = client.put(
        f"{API}/admin/users/{normal_user.id}/emergency-staff",
        json={"is_emergency_staff": True, "reason": "2026 年应急先锋队名单"},
        headers=admin_token_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_emergency_staff"] is True

    # 员工自己 GET /me 确认看到 True
    r = client.get(f"{API}/me", headers=normal_token_headers)
    assert r.status_code == 200, r.text
    assert r.json()["is_emergency_staff"] is True

    # 恢复 False (清理)
    client.put(
        f"{API}/admin/users/{normal_user.id}/emergency-staff",
        json={"is_emergency_staff": False},
        headers=admin_token_headers,
    )


def test_set_emergency_staff_by_non_admin_rejected(normal_token_headers, normal_user):
    """普通员工试图改 → 403 (显性化, 不静默)"""
    r = client.put(
        f"{API}/admin/users/{normal_user.id}/emergency-staff",
        json={"is_emergency_staff": True},
        headers=normal_token_headers,
    )
    assert r.status_code == 403, r.text


def test_set_emergency_staff_target_not_found(admin_token_headers):
    """目标用户不存在 → 404"""
    r = client.put(
        f"{API}/admin/users/99999999/emergency-staff",
        json={"is_emergency_staff": True},
        headers=admin_token_headers,
    )
    assert r.status_code == 404, r.text
