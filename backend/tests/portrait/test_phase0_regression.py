"""Phase 0 功能修复回归测试 (重构方案)

覆盖三个 P0:
  1. F12 家访矩阵组长路径 —— 原实现 Python `in` 误用于 SQLAlchemy Subquery,
     任何 team_id 非空用户访问必然 TypeError → 500, 且此前零测试覆盖
  2. 出入境批量导入 —— 原实现循环内 db.rollback(), 第 N 行失败会回滚此前
     所有成功行且虚报 success; 现为行级 savepoint
  3. 家访列表分页 total —— 原为 len(本页 items), 恒等于页大小
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.portrait import models as pmodels
from app.portrait.schemas.entry_exit import EntryExitImportRow
from app.portrait.services.entry_exit_service import entry_exit_service
from app.portrait.services.home_visit_service import home_visit_service
from app.portrait.schemas.home_visit import HomeVisitCreate

client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


def _mk_user(db, username, ehr_id, team_id=None, is_superuser=False):
    u = models.User(
        username=username, ehr_id=ehr_id, name=username,
        department="P0回归", hashed_password="x",
        is_active=True, is_superuser=is_superuser, team_id=team_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_team(db, name):
    t = models.Team(name=name, department="P0回归")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture(scope="function", autouse=True)
def _ensure_admin_approver(admin_user: models.User):  # noqa: ARG001
    """家访 submit 的审批人解析取第一个 superuser, 隔离空库必须先有 (Phase 1.1)"""
    assert admin_user.is_superuser


def _visit_payload(visited_ehr_id: str) -> dict:
    return {
        "visited_ehr_id": visited_ehr_id,
        "visit_year": 2026,
        "visit_time": "2026-03-10T10:00:00",
        "visit_method": "线下",
        "is_visited": True,
        "visit_content": "P0 回归测试家访",
        "visit_address": "回归地址",
    }


# ------------------------------------------------------------- 1. 矩阵组长路径
class TestMatrixLeaderPath:
    def test_leader_matrix_no_500(self, db: Session):
        """组长 (team_id 非空) 访问矩阵 —— 修复前必然 TypeError 500"""
        team = _mk_team(db, "P0矩阵组")
        leader = _mk_user(db, "p0_leader", "3100001", team_id=team.id)
        member = _mk_user(db, "p0_member", "3100002", team_id=team.id)

        record = home_visit_service.create_draft(
            db, visitor=leader, data=HomeVisitCreate(**_visit_payload(member.ehr_id))
        )
        home_visit_service.submit(db, visit_id=record.id, viewer=leader)

        r = client.get(f"{API_PORTRAIT}/home-visits/matrix", headers=_headers(leader))
        assert r.status_code == 200, r.text
        body = r.json()
        # pending 默认计入 (include_pending=True)
        ehrs = {row.get("ehr_id") for row in body.get("rows", [])}
        assert member.ehr_id in ehrs

    def test_leader_matrix_excludes_other_team(self, db: Session):
        team_a = _mk_team(db, "P0矩阵A组")
        team_b = _mk_team(db, "P0矩阵B组")
        leader = _mk_user(db, "p0_la", "3200001", team_id=team_a.id)
        member_a = _mk_user(db, "p0_ma", "3200002", team_id=team_a.id)
        # B 组的记录必须由 B 组自己的组长建 (C1: 跨组成员家访会被拒),
        # 从而验证 A 组长的矩阵确实看不到 B 组数据
        leader_b = _mk_user(db, "p0_lb", "3200004", team_id=team_b.id)
        member_b = _mk_user(db, "p0_mb", "3200003", team_id=team_b.id)

        rec_a = home_visit_service.create_draft(
            db, visitor=leader, data=HomeVisitCreate(**_visit_payload(member_a.ehr_id))
        )
        home_visit_service.submit(db, visit_id=rec_a.id, viewer=leader)
        rec_b = home_visit_service.create_draft(
            db, visitor=leader_b, data=HomeVisitCreate(**_visit_payload(member_b.ehr_id))
        )
        home_visit_service.submit(db, visit_id=rec_b.id, viewer=leader_b)

        r = client.get(f"{API_PORTRAIT}/home-visits/matrix", headers=_headers(leader))
        assert r.status_code == 200, r.text
        rows = {row.get("ehr_id"): row for row in r.json().get("rows", [])}
        assert member_a.ehr_id in rows
        assert member_b.ehr_id not in rows


# ------------------------------------------------------------- 2. 导入 savepoint
class TestEntryExitImportSavepoint:
    @staticmethod
    def _row(n: int, ehr: str) -> EntryExitImportRow:
        return EntryExitImportRow(
            row_number=n, seq=n, ehr_id=ehr,
            name=f"导入{n}", team_name="导入组", position="柜员",
            certificate_no=f"P0CERT{n}", outbound_reason="培训",
            destination="香港",
            apply_depart_at=datetime(2026, 3, 1, 8, 0),
            apply_return_at=datetime(2026, 3, 5, 18, 0),
            certificate_type="港澳通行证", apply_type="首次申请",
            team_approver="审批人", year=2026,
        )

    def test_mixed_rows_success_count_matches_db(self, db: Session):
        u1 = _mk_user(db, "p0_ie1", "3300001")
        u2 = _mk_user(db, "p0_ie2", "3300002")
        # 中间一行 EHR 不存在 —— 修复前它会把前后成功行一起回滚掉
        rows = [self._row(1, u1.ehr_id), self._row(2, "9999999"), self._row(3, u2.ehr_id)]

        summary = entry_exit_service.import_rows(db, rows=rows)

        assert summary.success_count == 2, summary.failed_rows
        assert summary.failed_count == 1
        assert summary.failed_rows[0]["row_number"] == 2
        in_db = db.query(pmodels.EntryExitRecord).filter(
            pmodels.EntryExitRecord.ehr_id.in_([u1.ehr_id, u2.ehr_id])
        ).count()
        assert in_db == 2, "失败行不得牵连已成功行 (修复前此处丢数据)"


# ------------------------------------------------------------- 3. 分页 total
class TestHomeVisitPaginationTotal:
    def test_total_is_query_count_not_page_size(self, db: Session):
        team = _mk_team(db, "P0分页组")
        leader = _mk_user(db, "p0_pg", "3400001", team_id=team.id)
        for i in range(3):
            member = _mk_user(db, f"p0_pgm{i}", f"340001{i}", team_id=team.id)
            rec = home_visit_service.create_draft(
                db, visitor=leader,
                data=HomeVisitCreate(**_visit_payload(member.ehr_id)),
            )
            home_visit_service.submit(db, visit_id=rec.id, viewer=leader)

        r = client.get(
            f"{API_PORTRAIT}/home-visits",
            headers=_headers(leader),
            params={"limit": 2},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 3, "total 应为查询基数而非本页条数"
        assert len(body["items"]) == 2
