"""组长判据单元测试（决策 1，2026-10-16）

组长 ≡ 该用户是所在组的 ``teams.leader_id``。

历史判据是「``team_id`` 非空」—— 任何员工只要被分了个组就自动获得组长权限。
本文件锁定新判据的四种边界，是决策 1 全部改动（service 收口 + 前端 + 管理界面）
的地基: 判据本身错了，下游全错。

隔离: 根 tests/conftest.py 已推广函数级内存库, 本文件不自带 shim。
"""
import pytest
from sqlalchemy.orm import Session

from app import models
from app.services.team_service import TeamService


@pytest.fixture(scope="function")
def team(db: Session) -> models.Team:
    t = models.Team(name="判据测试组", department="测试部")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _mk_user(db: Session, name: str, team_id=None, is_superuser=False) -> models.User:
    u = models.User(
        username=f"judge_{name}",
        ehr_id=f"{abs(hash(name)) % 9000000 + 1000000}"[-7:],
        name=name,
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=is_superuser,
        team_id=team_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_user_without_team_is_not_leader(db: Session):
    """没分组的员工 —— 连组长都不是"""
    u = _mk_user(db, "无组员工")
    assert TeamService.is_leader(db, u) is False


def test_team_member_without_leader_id_is_not_leader(db: Session, team):
    """组员但该组没指定组长 (leader_id 为 NULL) → 不是组长。

    这是存量数据的现状: 10 个组的 leader_id 全是 NULL。
    """
    u = _mk_user(db, "普通组员", team_id=team.id)
    assert TeamService.is_leader(db, u) is False


def test_team_member_with_other_leader_is_not_leader(db: Session, team):
    """组员, 但组长是别人 → 不是组长 (旧判据下他会是组长)"""
    leader = _mk_user(db, "正组长", team_id=team.id)
    other = _mk_user(db, "同组其他人", team_id=team.id)
    team.leader_id = leader.id
    db.commit()

    assert TeamService.is_leader(db, other) is False, "同组不等于组长"
    assert TeamService.is_leader(db, leader) is True


def test_leader_of_another_team_is_not_leader(db: Session, team):
    """A 组的组长调到 B 组后, 在 B 组不再是组长 (组长身份跟着组走)"""
    team_a = models.Team(name="甲组", department="甲部")
    db.add(team_a)
    db.commit()
    db.refresh(team_a)

    leader = _mk_user(db, "调组组长", team_id=team_a.id)
    team_a.leader_id = leader.id
    db.commit()
    assert TeamService.is_leader(db, leader) is True

    # 调到 B 组
    leader.team_id = team.id
    db.commit()
    assert TeamService.is_leader(db, leader) is False, "换组后旧组组长身份应失效"


def test_superuser_is_not_counted_as_leader(db: Session, team):
    """超管不算组长 —— 超管权限走 is_superuser 分支, 两者不要混为一谈。

    否则调用点写成 "is_superuser or is_leader" 与 "is_leader" 两种写法会不等价。
    """
    boss = _mk_user(db, "超管", team_id=team.id, is_superuser=True)
    team.leader_id = boss.id
    db.commit()

    assert TeamService.is_leader(db, boss) is False
    assert boss.is_superuser is True


def test_leader_without_team_is_not_leader(db: Session):
    """无组的 leader 字段无从谈起 → False"""
    u = _mk_user(db, "孤立用户")
    assert TeamService.is_leader(db, u) is False


def test_none_user_is_not_leader(db: Session):
    """None 传入不得抛异常 (Rule 12: 不能靠崩溃暴露问题)"""
    assert TeamService.is_leader(db, None) is False
