"""台账撤回审批的权限边界 (2026-10-21)

背景: `POST /api/v1/approvals/ledgers/{id}/cancel` 原有一段"组长代组员撤回"的分支,
它查询 `models.team_members` —— 该表从未在 ORM 中定义过。任何"非创建人 + 非超管 +
台账有归属组"的调用都会抛 AttributeError -> 500, 而不是 403。

已按决策删除该分支: 撤回仅限 台账创建人本人 或 超级管理员。
本文件锁定这条边界, 防止回归成 500 或被悄悄放宽。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models
from app.core.config import settings
from app.main import app
from app.services.auth_service import create_access_token
from tests.utils.user import create_random_user

client = TestClient(app)


@pytest.fixture
def team(db: Session) -> models.Team:
    team = models.Team(name="撤回测试组", department="测试部门")
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@pytest.fixture
def pending_ledger(db: Session, normal_user: models.User, team: models.Team) -> models.Ledger:
    """一台处于待审批状态、归属到组的台账, 创建人是 normal_user。"""
    ledger = models.Ledger(
        name="待撤回台账",
        status="active",
        approval_status="pending",
        team_id=team.id,
        created_by_id=normal_user.id,
        updated_by_id=normal_user.id,
        data={},
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return ledger


def _headers(user: models.User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_non_creator_non_superuser_gets_403_not_500(
    db: Session, pending_ledger: models.Ledger, normal_user: models.User
):
    """同组普通成员调用撤回 -> 403 (原先是 500 AttributeError)。"""
    other = create_random_user(db, email="other@example.com", password="User123!")

    r = client.post(
        f"{settings.API_V1_STR}/approvals/ledgers/{pending_ledger.id}/cancel",
        headers=_headers(other),
    )

    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "无权取消此台账的审批流程"
    # 台账状态未被改动
    db.refresh(pending_ledger)
    assert pending_ledger.status == "active"
    assert pending_ledger.approval_status == "pending"


def test_creator_passes_permission_gate(
    db: Session, pending_ledger: models.Ledger, normal_user: models.User
):
    """创建人本人通过权限闸门 —— 后续因无工作流实例返回 400, 而不是 403。

    断言 400 而非 403, 正是为了证明"权限闸门已放行", 避免把"因权限被拒"误当成通过。
    """
    r = client.post(
        f"{settings.API_V1_STR}/approvals/ledgers/{pending_ledger.id}/cancel",
        headers=_headers(normal_user),
    )

    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "台账没有活动的工作流实例"


def test_superuser_passes_permission_gate(
    db: Session, pending_ledger: models.Ledger, admin_user: models.User
):
    """超管通过权限闸门 —— 同样因无工作流实例返回 400。"""
    r = client.post(
        f"{settings.API_V1_STR}/approvals/ledgers/{pending_ledger.id}/cancel",
        headers=_headers(admin_user),
    )

    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "台账没有活动的工作流实例"
