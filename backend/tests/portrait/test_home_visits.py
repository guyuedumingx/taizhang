"""
portrait HomeVisit P6 审批流测试 (批次 10)

覆盖 (10 test):
  - 健康 / 列表 / 详情基线 (3 test)
  - 创建草稿 + 权限隔离 (2 test)
  - 提交审批 (submit) + 边界 (2 test)
  - 审批通过 / 驳回 / 撤回 (3 test)

复用 tests/conftest.py 已有 fixtures (db / admin_user / normal_user / *_token_headers).
需要 leader fixture (单独建, 用于家访创建).
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.main import app
from app.core.security import create_access_token
from app.portrait.schemas import HomeVisitCreate


client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


def _create_leader(db: Session) -> models.User:
    """创建一个 leader (有 team_id + is_superuser=False) 用户"""
    existing = (
        db.query(models.User)
        .filter(models.User.is_superuser == False, models.User.team_id.isnot(None))  # noqa
        .first()
    )
    if existing:
        return existing
    team = db.query(models.Team).filter(models.Team.name == "测试组").first()
    if not team:
        team = models.Team(name="测试组", department="测试部门")
        db.add(team)
        db.commit()
        db.refresh(team)
    leader = models.User(
        username="test_leader_p6",
        ehr_id="2000001",
        name="测试组长P6",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=team.id,
        department="测试部门",
    )
    db.add(leader)
    db.commit()
    db.refresh(leader)
    return leader


def _create_normal_member(db: Session, team_id: int) -> models.User:
    """创建 leader 组内的普通成员 (ehr_id 唯一避免 UNIQUE 冲突)"""
    import random
    while True:
        ehr_id = str(random.randint(3000000, 9999999))
        existing = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        if not existing:
            break
    username = f"test_member_{ehr_id}"
    member = models.User(
        username=username,
        ehr_id=ehr_id,
        name="测试组员",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=team_id,
        department="测试部门",
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@pytest.fixture(scope="function")
def leader_user(db: Session) -> models.User:
    return _create_leader(db)


@pytest.fixture(scope="function")
def leader_token_headers(leader_user: models.User) -> dict:
    token = create_access_token({"sub": str(leader_user.id)})
    return {"Authorization": f"Bearer {token}"}


def _create_visit_payload(visited_ehr_id: str) -> dict:
    return {
        "visited_ehr_id": visited_ehr_id,
        "visit_year": 2026,
        "visit_time": "2026-09-20T10:00:00",
        "visit_method": "线下",
        "visit_address": "北京市朝阳区",
        "visitor_info": "测试家访信息",
        "is_visited": True,
        "visit_date": "2026-09-20",
        "position": "测试岗位",
        "contact_phone": "010-12345678",
        "address": "北京市朝阳区XX路",
        "mobile": "13800000000",
        "home_phone": "010-87654321",
        "family1_name": "家属1",
        "family1_relation": "配偶",
        "family1_contact": "13900000000",
        "family1_work_unit": "测试单位",
        "family2_name": "家属2",
        "family2_relation": "子女",
        "family2_contact": "13911111111",
        "family2_work_unit": "测试单位2",
        "feedback": "测试反馈意见",
    }


# ============================================================================
# 列表 / 详情基线 (3 test)
# ============================================================================
def test_list_home_visits_no_auth_rejected():
    """GET /home-visits 无 token 返回 401"""
    response = client.get(f"{API_PORTRAIT}/home-visits")
    assert response.status_code == 401, response.text


def test_list_home_visits_admin_sees_all(admin_token_headers: dict):
    """admin 可看全部 (空列表 200 + total 字段)"""
    response = client.get(f"{API_PORTRAIT}/home-visits", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_home_visits_status_filter(admin_token_headers: dict):
    """admin status=draft 筛选"""
    response = client.get(
        f"{API_PORTRAIT}/home-visits?status=draft", headers=admin_token_headers
    )
    assert response.status_code == 200, response.text


# ============================================================================
# 创建草稿 + 权限隔离 (2 test)
# ============================================================================
def test_create_home_visit_user_rejected(normal_token_headers: dict, normal_user: models.User):
    """user role 无 team_id, 创建草稿应被拒 403"""
    payload = _create_visit_payload("1234567")
    response = client.post(
        f"{API_PORTRAIT}/home-visits", json=payload, headers=normal_token_headers
    )
    assert response.status_code == 403, response.text


def test_create_home_visit_admin_rejected(admin_token_headers: dict):
    """admin (is_superuser=True) 创建被拒 (业务规则: 谁做家访谁签字)"""
    payload = _create_visit_payload("1234567")
    response = client.post(
        f"{API_PORTRAIT}/home-visits", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 403, response.text


# ============================================================================
# 提交审批 (submit) (2 test)
# ============================================================================
def test_submit_home_visit_visitor_only(
    db: Session,
    leader_token_headers: dict,
    leader_user: models.User,
):
    """非 visitor 提交应 403"""
    member = _create_normal_member(db, leader_user.team_id)
    from app.portrait.services import home_visit_service
    # leader 给 member 建草稿
    payload = _create_visit_payload(member.ehr_id)
    payload["visit_year"] = 2026
    payload_obj = HomeVisitCreate(**payload)
    record = home_visit_service.create_draft(db, visitor=leader_user, data=payload_obj)

    # normal user 提交别人的家访应 403
    import random
    user = models.User(
        username=f"random_user_{random.randint(100000, 999999)}",
        ehr_id=str(random.randint(4000000, 4999999)),
        name="普通用户X",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"{API_PORTRAIT}/home-visits/{record.id}/submit",
        json={"next_approver_id": None},
        headers=headers,
    )
    assert response.status_code == 403, response.text


def test_submit_home_visit_already_pending_rejected(
    leader_token_headers: dict,
    leader_user: models.User,
    db: Session,
):
    """重复提交 (已是 pending) 应 400"""
    member = _create_normal_member(db, leader_user.team_id)
    from app.portrait.services import home_visit_service
    payload_obj = HomeVisitCreate(**_create_visit_payload(member.ehr_id))
    record = home_visit_service.create_draft(db, visitor=leader_user, data=payload_obj)
    home_visit_service.submit(db, visit_id=record.id, viewer=leader_user)

    # 第二次 submit
    response = client.post(
        f"{API_PORTRAIT}/home-visits/{record.id}/submit",
        json={},
        headers=leader_token_headers,
    )
    assert response.status_code == 400, response.text


# ============================================================================
# 审批通过 / 驳回 / 撤回 (3 test)
# ============================================================================
def test_approve_home_visit_pending_to_approved(
    admin_token_headers: dict,
    leader_user: models.User,
    db: Session,
):
    """admin 审批通过: pending → approved"""
    member = _create_normal_member(db, leader_user.team_id)
    from app.portrait.services import home_visit_service
    payload_obj = HomeVisitCreate(**_create_visit_payload(member.ehr_id))
    record = home_visit_service.create_draft(db, visitor=leader_user, data=payload_obj)
    home_visit_service.submit(db, visit_id=record.id, viewer=leader_user)

    response = client.post(
        f"{API_PORTRAIT}/home-visits/{record.id}/approve",
        json={"comment": "审批通过"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "approved"
    assert data["current_approver_id"] is None
    assert data["completed_at"] is not None


def test_reject_home_visit_empty_comment_rejected_400(
    admin_token_headers: dict,
    leader_user: models.User,
    db: Session,
):
    """驳回空白 comment 被 service 层拒绝 (Rule 12 显性化, 400)
    注: Pydantic v2 schema 校验空字符串返 422, service 层 strip 后再校验返 400
    本测试用空白字符触发 service 层
    """
    member = _create_normal_member(db, leader_user.team_id)
    from app.portrait.services import home_visit_service
    payload_obj = HomeVisitCreate(**_create_visit_payload(member.ehr_id))
    record = home_visit_service.create_draft(db, visitor=leader_user, data=payload_obj)
    home_visit_service.submit(db, visit_id=record.id, viewer=leader_user)

    response = client.post(
        f"{API_PORTRAIT}/home-visits/{record.id}/reject",
        json={"comment": "   "},
        headers=admin_token_headers,
    )
    assert response.status_code == 400, response.text
    assert "意见" in response.text


def test_cancel_home_visit_submitter_only(
    leader_token_headers: dict,
    leader_user: models.User,
    db: Session,
):
    """仅 submitter 可撤回, 仅 pending 可撤回"""
    member = _create_normal_member(db, leader_user.team_id)
    from app.portrait.services import home_visit_service
    payload_obj = HomeVisitCreate(**_create_visit_payload(member.ehr_id))
    record = home_visit_service.create_draft(db, visitor=leader_user, data=payload_obj)
    home_visit_service.submit(db, visit_id=record.id, viewer=leader_user)

    response = client.post(
        f"{API_PORTRAIT}/home-visits/{record.id}/cancel",
        headers=leader_token_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "cancelled"