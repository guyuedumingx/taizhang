"""
G7 组员调换历史测试 (Week 3 P0.5, PRD §11.4)

覆盖三组:
  A. 写入语义      — 首次调组/连续调组/短路/退组占位/零半截写入
  B. 集成与回归    — 三个挂钩点, 证明现有调用不受影响
  C. 权限与端点    — 组名重名不越权 / 删除规则 / 无新增入口

测试隔离: 根 tests/conftest.py 的 db 已是**函数级隔离内存库** (StaticPool +
create_all), 每个用例开始时库是全新的 —— 因此本文件不再需要任何"事后清理"
代码 (原先按 id 精确删库的 _CREATED_USERS/_CREATED_TEAMS 机制已随之移除,
在隔离库下反而会因跨用例 detached 对象抛 DetachedInstanceError)。
"""
import uuid

import pytest
from fastapi import HTTPException

from app import models, schemas
from app.core.config import settings
from app.core.security import create_access_token
from app.portrait import models as portrait_models
from app.portrait.models import GroupTransferHistory
from app.portrait.services.group_transfer_service import (
    GROUP_UNASSIGNED,
    record_transfer,
)
from app.services.team_service import TeamService
from app.services.user_service import UserService

API = f"{settings.API_V1_STR}/portrait/group-transfers"
USERS_API = f"{settings.API_V1_STR}/users"

# 本文件造出来的对象不再需要事后清理: 根 conftest 的 db 是函数级隔离内存库,
# 每个用例一个全新空库, 用例结束即销毁。


def _mk_team(db, name: str) -> models.Team:
    team = models.Team(name=name, department="G7测试部门", description="G7 测试临时组")
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def _mk_user(db, name: str, team_id=None, is_superuser=False, leader: bool = False) -> models.User:
    """造一个唯一 EHR 号的用户 (EHR 7 位, 与业务校验一致)

    决策 1: ``leader=True`` 会把该用户设为其所在组的 ``teams.leader_id`` ——
    组长判据不再是有 team_id 就算, 组员默认不是组长。
    """
    ehr_id = None
    for _ in range(20):
        candidate = f"{uuid.uuid4().int % 9000000 + 1000000}"
        if not db.query(models.User).filter(models.User.ehr_id == candidate).first():
            ehr_id = candidate
            break
    if ehr_id is None:
        raise RuntimeError("造不出唯一 EHR 号")

    user = models.User(
        username=f"g7_{uuid.uuid4().hex[:12]}",
        ehr_id=ehr_id,
        name=name,
        department="G7测试部门",
        hashed_password="x",  # noqa: S105 - 测试数据, 不会被用来登录
        is_active=True,
        is_superuser=is_superuser,
        team_id=team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if leader and team_id is not None:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if team is not None:
            team.leader_id = user.id
            db.commit()
            db.refresh(team)
    return user


def _token(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def purge(db):
    """清掉本文件造的调换历史 (写语义测试用)

    隔离库下每个用例本来就是空库, 所以这行实际是空操作; 保留它是为了
    "前置条件显式化" —— 万一哪天 conftest 改回共享库, 这里仍能保证
    "本用例开始时没有存量调换记录" 这个断言前提是成立的。
    """

    def _do():
        db.query(GroupTransferHistory).delete(synchronize_session=False)
        db.commit()

    return _do


def _records(db, user) -> list:
    """按时间正序返回某人的调换记录 (断言用, 绕过 session 缓存)"""
    db.expire_all()
    return (
        db.query(GroupTransferHistory)
        .filter(GroupTransferHistory.user_id == user.id)
        .order_by(GroupTransferHistory.id.asc())
        .all()
    )


# ============================================================================
# A. 写入语义
# ============================================================================
def test_first_transfer_records_from_group_and_does_not_backfill(db, purge):
    """首次调组: 恰好 1 条, from=原组 / to=新组, 开区间。不补录不造假"""
    purge()
    team_a, team_b = _mk_team(db, "甲组"), _mk_team(db, "乙组")
    user = _mk_user(db, "李四", team_id=team_a.id)
    operator = _mk_user(db, "管理员甲")

    assert _records(db, user) == []  # 前置: 无存量

    record_transfer(db, user=user, to_team_id=team_b.id, operator_user_id=operator.id)

    recs = _records(db, user)
    assert len(recs) == 1, "首次调组应恰好写 1 条, 不得补录历史"
    rec = recs[0]
    assert rec.from_group == "甲组"
    assert rec.to_group == "乙组"
    assert rec.from_team_id == team_a.id, "授权靠 team_id, 必须记对"
    assert rec.to_team_id == team_b.id
    assert rec.leave_date is None, "当前所在组必须是开区间"
    assert rec.operator_user_id == operator.id


def test_consecutive_transfers_close_previous_intervals(db, purge):
    """A→B→C 两次调组 → 2 条 (一次调组一条, 不补录进入 A 的那条),
    前一条 leave_date == 下一条 transfer_date, 恰好 1 条开区间"""
    purge()
    team_a, team_b, team_c = _mk_team(db, "甲组"), _mk_team(db, "乙组"), _mk_team(db, "丙组")
    user = _mk_user(db, "王五", team_id=team_a.id)
    operator = _mk_user(db, "管理员乙")

    record_transfer(db, user=user, to_team_id=team_b.id, operator_user_id=operator.id)
    user.team_id = team_b.id
    db.commit()
    record_transfer(db, user=user, to_team_id=team_c.id, operator_user_id=operator.id)

    recs = _records(db, user)
    assert len(recs) == 2, "两次调组 = 2 条; 进入甲组那条不补录"
    assert recs[0].leave_date == recs[1].transfer_date, "前一条的离组时间 = 下一条的调组时间"
    open_recs = [r for r in recs if r.leave_date is None]
    assert len(open_recs) == 1, "任何时刻最多 1 条开区间记录"
    assert open_recs[0].to_group == "丙组"


def test_same_team_short_circuits_and_writes_nothing(db, purge):
    """调组到当前组 → 返回 None 且表里 0 条 (前端每次编辑都提交 team_id, 没这条就造假)"""
    purge()
    team_a = _mk_team(db, "甲组")
    user = _mk_user(db, "赵六", team_id=team_a.id)
    operator = _mk_user(db, "管理员丙")

    result = record_transfer(
        db, user=user, to_team_id=team_a.id, operator_user_id=operator.id
    )

    assert result is None
    assert _records(db, user) == [], "组别未变不得写库"


def test_transfer_to_unassigned_uses_placeholder(db, purge):
    """退组 (to_team_id=None) → to_group == 「未分组」, to_team_id 为 NULL"""
    purge()
    team_a = _mk_team(db, "甲组")
    user = _mk_user(db, "孙七", team_id=team_a.id)
    operator = _mk_user(db, "管理员丁")

    record_transfer(db, user=user, to_team_id=None, operator_user_id=operator.id)

    recs = _records(db, user)
    assert len(recs) == 1
    assert recs[0].to_group == GROUP_UNASSIGNED
    assert recs[0].to_team_id is None
    assert recs[0].from_team_id == team_a.id, "退组记录仍属原组, 原组长必须看得到"


def test_unknown_team_raises_before_any_write(db, purge):
    """目标团队不存在 → 400 且表里 0 条 (零半截写入)"""
    purge()
    team_a = _mk_team(db, "甲组")
    user = _mk_user(db, "周八", team_id=team_a.id)
    operator = _mk_user(db, "管理员戊")

    with pytest.raises(HTTPException) as exc:
        record_transfer(db, user=user, to_team_id=99999999, operator_user_id=operator.id)
    assert exc.value.status_code == 400
    assert _records(db, user) == [], "抛错前不得留下任何记录"


@pytest.mark.parametrize("operator_id", [None, 99999999])
def test_missing_or_unknown_operator_rejected(db, purge, operator_id):
    """operator 缺失/不存在 → 400 且 0 条 (operator 三列非空, 不能伪造也不能静默跳过)"""
    purge()
    team_a, team_b = _mk_team(db, "甲组"), _mk_team(db, "乙组")
    user = _mk_user(db, "吴九", team_id=team_a.id)

    with pytest.raises(HTTPException) as exc:
        record_transfer(db, user=user, to_team_id=team_b.id, operator_user_id=operator_id)
    assert exc.value.status_code == 400
    assert _records(db, user) == []


# ============================================================================
# B. 集成与回归
# ============================================================================
def test_update_user_name_only_writes_no_record(db, purge, normal_user):
    """只改名字不改组 → 0 条记录 (证明现有调用不因挂钩变红)"""
    purge()
    team_a = _mk_team(db, "甲组")
    normal_user.team_id = team_a.id
    db.commit()

    UserService.update_user(
        db,
        user_id=normal_user.id,
        user_in=schemas.UserUpdate(name="改过的名字"),
        operator_user_id=normal_user.id,
    )

    assert _records(db, normal_user) == [], "没改组就不该有调换记录"


def test_update_user_team_change_without_operator_rejected(db, purge, normal_user):
    """改组不传操作人 → 400, 且 user.team_id 仍是旧值 (事务没留下半截)"""
    purge()
    team_a, team_b = _mk_team(db, "甲组"), _mk_team(db, "乙组")
    normal_user.team_id = team_a.id
    db.commit()
    user_update = schemas.UserUpdate(team_id=team_b.id)

    with pytest.raises(HTTPException) as exc:
        UserService.update_user(
            db, user_id=normal_user.id, user_in=user_update, operator_user_id=None
        )
    assert exc.value.status_code == 400

    db.expire_all()
    assert db.query(models.User).get(normal_user.id).team_id == team_a.id, "组别不能被改掉"
    assert _records(db, normal_user) == []


def test_add_user_to_team_same_team_rejected_writes_nothing(db, purge):
    """同组重复加入 → 400 且 0 条 (证明挂钩点在 raise 之后)"""
    purge()
    team_a = _mk_team(db, "甲组")
    user = _mk_user(db, "郑十", team_id=team_a.id)
    operator = _mk_user(db, "管理员己")

    with pytest.raises(HTTPException) as exc:
        TeamService.add_user_to_team(
            db, team_id=team_a.id, user_id=user.id, current_user_id=operator.id
        )
    assert exc.value.status_code == 400
    assert _records(db, user) == [], "失败的加入操作不得留下记录"


def test_add_and_remove_team_writes_records(db, purge):
    """加入 + 退组: 2 条, 退组那条 to_group=未分组 且原组仍记着 team_id"""
    purge()
    team_a, team_b = _mk_team(db, "甲组"), _mk_team(db, "乙组")
    user = _mk_user(db, "陈十二")  # 初始无组
    operator = _mk_user(db, "管理员庚")

    TeamService.add_user_to_team(
        db, team_id=team_a.id, user_id=user.id, current_user_id=operator.id
    )
    recs = _records(db, user)
    assert len(recs) == 1
    assert recs[0].from_group == GROUP_UNASSIGNED and recs[0].from_team_id is None
    assert recs[0].to_group == "甲组" and recs[0].to_team_id == team_a.id

    TeamService.add_user_to_team(
        db, team_id=team_b.id, user_id=user.id, current_user_id=operator.id
    )
    recs = _records(db, user)
    assert len(recs) == 2
    assert recs[0].leave_date == recs[1].transfer_date, "换组要闭合上一条"

    TeamService.remove_user_from_team(
        db, team_id=team_b.id, user_id=user.id, current_user_id=operator.id
    )
    recs = _records(db, user)
    assert len(recs) == 3
    assert recs[2].to_group == GROUP_UNASSIGNED and recs[2].to_team_id is None
    assert recs[2].from_team_id == team_b.id
    db.expire_all()
    assert db.query(models.User).get(user.id).team_id is None


# ============================================================================
# C. 权限与端点
# ============================================================================
def test_duplicate_team_names_do_not_leak(db, purge, admin_user):
    """**安全回归**: 两个同名组, A 组组长看不到 B 组的记录。

    这是选 team_id 而不是组名做授权的全部理由 —— 开发库里就有 26 个都叫
    「外组」的行, 按名字过滤会让这些组长互相看到对方的员工。
    """
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    dup_name = f"重名组{uuid.uuid4().hex[:6]}"
    team_a, team_b = _mk_team(db, dup_name), _mk_team(db, dup_name)  # 同名, 不同 id
    assert team_a.id != team_b.id
    start_team = _mk_team(db, f"起点组{uuid.uuid4().hex[:6]}")  # 既不是 A 也不是 B

    leader_a = _mk_user(db, "A组长", team_id=team_a.id, leader=True)
    moved_user = _mk_user(db, "被调的人", team_id=start_team.id)
    operator = _mk_user(db, "管理员辛")

    # 起点组 → B 组 (两个 team_id 都跟 A 组无关)
    record_transfer(
        db, user=moved_user, to_team_id=team_b.id, operator_user_id=operator.id
    )
    moved_user.team_id = team_b.id
    db.commit()

    # A 组组长看列表: 必须 0 条
    r = client.get(API, headers=_token(leader_a))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 0, f"同名不等于同组, A 组组长不该看到 B 组记录, 实际 total={body['total']}"
    assert body["items"] == []

    # admin 看得到 (1 条)
    admin = admin_user  # 重构 Phase 1.1: 隔离空库无种子超管, 改用根 conftest 固件
    r = client.get(API, headers=_token(admin))
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1, "admin 应看到全部"


def test_name_filtering_would_leak_which_is_why_ids_are_used(db, purge):
    """**配套测试**: 证明"按组名过滤"确实会越权, 正是加 team_id 两列的理由。

    和 test_duplicate_team_names_do_not_leak 配对 —— 那条测的是接口行为 (对外),
    这条测的是底层查询语义 (对内), 防止有人日后把 service 改回按名字过滤而
    只看到接口测试因为数据恰好不同而侥幸通过。
    """
    from sqlalchemy import or_

    purge()
    dup_name = f"重名组{uuid.uuid4().hex[:6]}"
    team_a, team_b = _mk_team(db, dup_name), _mk_team(db, dup_name)
    start_team = _mk_team(db, f"起点组{uuid.uuid4().hex[:6]}")
    moved_user = _mk_user(db, "被调的人", team_id=start_team.id)
    operator = _mk_user(db, "管理员寅")
    record_transfer(
        db, user=moved_user, to_team_id=team_b.id, operator_user_id=operator.id
    )

    # 错的实现: 按组名过滤 → A 组组长会看到 B 组的记录
    leaked = (
        db.query(GroupTransferHistory)
        .filter(
            or_(
                GroupTransferHistory.from_group == dup_name,
                GroupTransferHistory.to_group == dup_name,
            )
        )
        .all()
    )
    assert len(leaked) >= 1, "按组名过滤确实会泄露 —— 这就是不能按名字做授权的证据"

    # 对的实现: 按 team_id 过滤 → A 组组长看不到 B 组的记录
    safe = (
        db.query(GroupTransferHistory)
        .filter(
            or_(
                GroupTransferHistory.from_team_id == team_a.id,
                GroupTransferHistory.to_team_id == team_a.id,
            )
        )
        .all()
    )
    assert len(safe) == 0, "按 team_id 过滤不泄露"


def test_leader_sees_only_own_team_records_in_items_and_total(db, purge):
    """组长只看到本组相关: items 和 total 两处都要过滤 (漏一处就是越权)"""
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    team_a, team_b = _mk_team(db, "本组"), _mk_team(db, "别组")
    leader = _mk_user(db, "本组长", team_id=team_a.id, leader=True)
    operator = _mk_user(db, "管理员壬")

    # 别人: 只在别组调换 → 本组长不该看到
    outsider = _mk_user(db, "外人", team_id=team_b.id)
    record_transfer(db, user=outsider, to_team_id=team_b.id, operator_user_id=operator.id)
    outsider.team_id = team_b.id
    db.commit()

    # 本组的人: 调进来 → 本组长该看到
    insider = _mk_user(db, "自己人")
    record_transfer(db, user=insider, to_team_id=team_a.id, operator_user_id=operator.id)
    insider.team_id = team_a.id
    db.commit()

    r = client.get(API, headers=_token(leader))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1, f"total 必须是 1, 实际 {body['total']}"
    assert [i["user_id"] for i in body["items"]] == [insider.id], "items 也必须过滤"


def test_leader_filtering_outsider_ehr_returns_empty_not_403(db, purge):
    """组长筛外组 EHR → 200 + total 0 (不泄露该 EHR 是否存在)"""
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    team_a, team_b = _mk_team(db, "本组"), _mk_team(db, "别组")
    leader = _mk_user(db, "本组长", team_id=team_a.id, leader=True)
    operator = _mk_user(db, "管理员癸")
    outsider = _mk_user(db, "外人", team_id=team_b.id)
    record_transfer(db, user=outsider, to_team_id=team_b.id, operator_user_id=operator.id)
    outsider.team_id = team_b.id
    db.commit()

    r = client.get(f"{API}?ehr_id={outsider.ehr_id}", headers=_token(leader))
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0


def test_user_without_team_gets_403(db, purge):
    """没有组的普通用户 → 403 (不静默降级成看全部)"""
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    loner = _mk_user(db, "无组的人")

    r = client.get(API, headers=_token(loner))
    assert r.status_code == 403, r.text


def test_no_create_endpoint(db, purge, admin_user):
    """POST → 405 (把「记录只由调组自动产生」锁成断言)"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    admin = admin_user  # 重构 Phase 1.1: 隔离空库无种子超管, 改用根 conftest 固件

    r = client.post(API, json={}, headers=_token(admin))
    assert r.status_code == 405, r.text


def test_admin_cannot_delete_open_interval_record(db, purge, admin_user):
    """admin 删「当前在组」记录 → 400 且记录仍在"""
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    team_a, team_b = _mk_team(db, "甲组"), _mk_team(db, "乙组")
    user = _mk_user(db, "被调的人", team_id=team_a.id)
    operator = _mk_user(db, "管理员子")
    record_transfer(db, user=user, to_team_id=team_b.id, operator_user_id=operator.id)
    user.team_id = team_b.id
    db.commit()
    rec = _records(db, user)[0]
    admin = admin_user  # 重构 Phase 1.1: 隔离空库无种子超管, 改用根 conftest 固件

    r = client.delete(f"{API}/{rec.id}", headers=_token(admin))
    assert r.status_code == 400, r.text
    assert "调回正确组别" in r.json()["detail"]
    assert _records(db, user), "记录必须还在"


def test_admin_can_delete_closed_record_and_leader_cannot(db, purge, admin_user):
    """已关闭记录: admin 能删 (204), 组长调 DELETE → 403 且记录仍在"""
    purge()
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    team_a, team_b, team_c = _mk_team(db, "甲组"), _mk_team(db, "乙组"), _mk_team(db, "丙组")
    user = _mk_user(db, "被调的人", team_id=team_a.id)
    operator = _mk_user(db, "管理员丑")
    record_transfer(db, user=user, to_team_id=team_b.id, operator_user_id=operator.id)
    user.team_id = team_b.id
    db.commit()
    record_transfer(db, user=user, to_team_id=team_c.id, operator_user_id=operator.id)
    user.team_id = team_c.id
    db.commit()
    closed = _records(db, user)[0]  # 甲组 → 乙组, 已闭合
    assert closed.leave_date is not None

    leader = _mk_user(db, "甲组长", team_id=team_a.id)
    r = client.delete(f"{API}/{closed.id}", headers=_token(leader))
    assert r.status_code == 403, r.text
    assert _records(db, user), "组长无权删除, 记录必须还在"

    admin = admin_user  # 重构 Phase 1.1: 隔离空库无种子超管, 改用根 conftest 固件
    r = client.delete(f"{API}/{closed.id}", headers=_token(admin))
    assert r.status_code == 204, r.text
    remaining = _records(db, user)
    assert len(remaining) == 1 and remaining[0].leave_date is None, "只该剩开区间那条"
