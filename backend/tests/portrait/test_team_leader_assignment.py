"""指定组长 (决策 1) 的服务端校验测试

组长判据 = 该用户是所在组的 ``teams.leader_id``。因此"谁能被指定为组长"
和"指定后判据是否成立"必须在服务端闭环, 否则:
  - 组长指向外组的人 → 两个组的组长字段同时失真
  - 指向不存在的用户 → 组长永远无人, 组内功能集体瘫掉

覆盖:
  - 指定本组成员 → 成功, 判据随之成立
  - 指定外组用户 → 400
  - 指定不存在的用户 → 400
  - 显式取消组长 (null) → 成功, 判据随之失效
  - 组长调离本组后, 该组判据失效 (组长身份跟着组走)

隔离: 根 tests/conftest.py 已推广函数级内存库, 本文件不自带 shim。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.services.team_service import TeamService

client = TestClient(app)
API_TEAMS = f"{settings.API_V1_STR}/teams"


@pytest.fixture(scope="function")
def admin_headers(db: Session) -> dict:
    u = models.User(
        username="leader_admin",
        ehr_id="3000001",
        name="组长管理员",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"Authorization": f"Bearer {create_access_token({'sub': str(u.id)})}"}


@pytest.fixture(scope="function")
def team(db: Session) -> models.Team:
    t = models.Team(name="甲组", department="甲部")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture(scope="function")
def other_team(db: Session) -> models.Team:
    t = models.Team(name="乙组", department="乙部")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _mk_user(db: Session, name: str, ehr: str, team_id=None) -> models.User:
    u = models.User(
        username=f"lead_{name}",
        ehr_id=ehr,
        name=name,
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=team_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _set_leader(admin_headers, team_id: int, leader_id):
    return client.put(
        f"{API_TEAMS}/{team_id}",
        headers=admin_headers,
        json={"leader_id": leader_id},
    )


# ------------------------------------------------------------------ 正常路径
def test_assign_member_as_leader_succeeds(db: Session, admin_headers, team):
    """指定本组成员为组长 → 成功, 且判据随之成立"""
    member = _mk_user(db, "本组员", "3000011", team_id=team.id)

    resp = _set_leader(admin_headers, team.id, member.id)
    assert resp.status_code == 200, resp.text

    db.expire_all()
    reloaded = db.query(models.Team).filter(models.Team.id == team.id).first()
    assert reloaded.leader_id == member.id
    assert TeamService.is_leader(db, member) is True, "指定后判据应成立"


def test_clear_leader_succeeds(db: Session, admin_headers, team):
    """显式传 null 取消组长 → 成功, 判据失效 (组回到"无组长"状态)"""
    member = _mk_user(db, "待取消组长", "3000012", team_id=team.id)
    _set_leader(admin_headers, team.id, member.id)

    resp = _set_leader(admin_headers, team.id, None)
    assert resp.status_code == 200, resp.text

    db.expire_all()
    reloaded = db.query(models.Team).filter(models.Team.id == team.id).first()
    assert reloaded.leader_id is None
    assert TeamService.is_leader(db, member) is False


# ------------------------------------------------------------------ 非法路径
def test_assign_user_from_other_team_rejected(db: Session, admin_headers, team, other_team):
    """组长指向外组的人 → 400, 理由要说清是"外组"而非笼统失败"""
    outsider = _mk_user(db, "外组人", "3000013", team_id=other_team.id)

    resp = _set_leader(admin_headers, team.id, outsider.id)
    assert resp.status_code == 400, resp.text
    assert "本组" in resp.json()["detail"], resp.text

    db.expire_all()
    reloaded = db.query(models.Team).filter(models.Team.id == team.id).first()
    assert reloaded.leader_id is None, "被拒的请求不该留下半截数据"


def test_assign_nonexistent_user_rejected(db: Session, admin_headers, team):
    """组长指向不存在的用户 → 400 (否则组内功能集体瘫掉且无人察觉)"""
    resp = _set_leader(admin_headers, team.id, 99999999)
    assert resp.status_code == 400, resp.text
    assert "不存在" in resp.json()["detail"], resp.text


# ------------------------------------------------------------------ 联动
def test_leader_leaving_team_loses_leadership(db: Session, admin_headers, team, other_team):
    """组长被调离本组 → 该组判据失效 (组长身份跟着组走, 不跟着人走)"""
    member = _mk_user(db, "要调走的组长", "3000014", team_id=team.id)
    _set_leader(admin_headers, team.id, member.id)

    db.expire_all()
    assert TeamService.is_leader(db, member) is True

    member.team_id = other_team.id
    db.commit()
    db.expire_all()

    assert TeamService.is_leader(db, member) is False, "调走后不该还能当原组组长"


# ------------------------------------------------------------------ 建组闭环
def _make_team_creator(db: Session, ehr: str, name: str) -> models.User:
    """造一个**非超管**但有 team:create 权限的建组人。

    casbin 的 manager 角色没有 team:create, 所以给普通用户挂 admin 角色。
    """
    from app.services.casbin_service import add_role_for_user

    u = models.User(
        username=f"creator_{name}",
        ehr_id=ehr,
        name=name,
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    add_role_for_user(str(u.id), "admin")
    return u


def test_creating_team_without_leader_leaves_group_leaderless(db: Session):
    """建组时未指定负责人 → 本组暂无组长, 且**创建者不被静默调组**。

    建组人是普通员工时, 把他自动调进新组当组长是"静默调组" —— 他被动换组
    却没人告知, 而且新建的组因带成员而无法删除。组内无组长是可观察的中间态
    (管理员在「编辑团队」里指定即可), 静默调组不可察。
    """
    creator = _make_team_creator(db, "3000021", "建组人")
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(creator.id)})}"}

    resp = client.post(
        API_TEAMS,
        headers=headers,
        json={"name": "新建甲组", "department": "甲部", "description": "建组测试"},
    )
    assert resp.status_code == 200, resp.text
    new_team_id = resp.json()["id"]

    db.expire_all()
    new_team = db.query(models.Team).filter(models.Team.id == new_team_id).first()
    assert new_team.leader_id is None, "未指定负责人时不该凭空指定一个组长"

    creator = db.query(models.User).filter(models.User.id == creator.id).first()
    assert creator.team_id is None, "建组不该把创建者静默调进新组"


def test_creating_team_with_leader_assigns_and_enrolls_them(db: Session, admin_headers):
    """建组时指定负责人 → 该人成为组长**并被调入本组**。

    组长必须是本组成员 (否则 leader_id 指向外组的人, 字段与判据失真),
    所以建组时指定负责人 = 把他作为首任组员拉进来。
    """
    member = _mk_user(db, "指定负责人", "3000022", team_id=None)

    resp = client.post(
        API_TEAMS,
        headers=admin_headers,
        json={
            "name": "指定负责人的组",
            "department": "甲部",
            "description": "建组测试",
            "leader_id": member.id,
        },
    )
    assert resp.status_code == 200, resp.text
    new_team_id = resp.json()["id"]

    db.expire_all()
    new_team = db.query(models.Team).filter(models.Team.id == new_team_id).first()
    assert new_team.leader_id == member.id

    member = db.query(models.User).filter(models.User.id == member.id).first()
    assert member.team_id == new_team_id, "负责人应被调入本组, 否则 leader_id 指向外组的人"
    assert TeamService.is_leader(db, member) is True, "指定后判据应立即成立"


def test_creating_team_with_nonexistent_leader_rejected(db: Session, admin_headers):
    """建组时指定不存在的负责人 → 400, 且不留下半截数据"""
    resp = client.post(
        API_TEAMS,
        headers=admin_headers,
        json={
            "name": "无效负责人的组",
            "department": "甲部",
            "description": "建组测试",
            "leader_id": 99999999,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "不存在" in resp.json()["detail"], resp.text

    db.expire_all()
    assert (
        db.query(models.Team).filter(models.Team.name == "无效负责人的组").first() is None
    ), "被拒的建组请求不该留下组"


def test_leader_moved_to_another_team_frees_old_group_leader_slot(
    db: Session, admin_headers, team, other_team
):
    """组长被调去别的组 → 原组的 leader_id 必须清空。

    决策 1 里 leader_id 是组长判据的唯一来源, 它若继续指着已调走的人,
    管理界面显示的"负责人"与实际判据不符 (组有组长, 但没人是组长)。
    """
    member = _mk_user(db, "要调走的组长", "3000023", team_id=team.id)
    _set_leader(admin_headers, team.id, member.id)
    # _set_leader 走 API → 另一个 Session 提交, 本会话的 identity map 是旧的
    db.expire_all()

    # 调入别组 (走 add_user_to_team, 与后台改组同一路径)
    from app.services.team_service import TeamService

    TeamService.add_user_to_team(db, other_team.id, member.id, member.id)

    db.expire_all()
    reloaded = db.query(models.Team).filter(models.Team.id == team.id).first()
    assert reloaded.leader_id is None, "组长调走后原组的组长位必须清空"
    assert TeamService.is_leader(db, member) is False


def test_leader_removed_from_team_frees_leader_slot(db: Session, admin_headers, team):
    """组长退组 → 该组 leader_id 清空"""
    member = _mk_user(db, "退组的组长", "3000024", team_id=team.id)
    _set_leader(admin_headers, team.id, member.id)
    db.expire_all()  # 同上: API 用的是另一个 Session

    from app.services.team_service import TeamService

    TeamService.remove_user_from_team(db, team.id, member.id, member.id)

    db.expire_all()
    reloaded = db.query(models.Team).filter(models.Team.id == team.id).first()
    assert reloaded.leader_id is None, "组长退组后组长位必须清空"


def test_superuser_creating_team_leaves_leader_unset(db: Session, admin_headers):
    """超管建组 → leader_id 留空 (组待指定组长)。

    超管不算组长 (is_leader 对超管返回 False), 把 leader_id 指向超管会让
    组的 leader 字段与判据失真 —— 字段说有组长, 实际没人能当这个组长。
    """
    resp = client.post(
        API_TEAMS,
        headers=admin_headers,
        json={"name": "超管建的组", "department": "丙部", "description": "超管建组"},
    )
    assert resp.status_code == 200, resp.text
    new_team_id = resp.json()["id"]

    db.expire_all()
    new_team = db.query(models.Team).filter(models.Team.id == new_team_id).first()
    assert new_team.leader_id is None, "超管建组不该把 leader_id 指向超管本人"

    creator = db.query(models.User).filter(models.User.username == "leader_admin").first()
    assert creator.team_id is None, "超管建组不该被静默调进新组"
