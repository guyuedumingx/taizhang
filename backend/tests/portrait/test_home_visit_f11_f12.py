"""
portrait 家访 F11 批量导入 / F12 年度矩阵 / 批量导出 Excel 测试

覆盖:
  - F11: 正常入库 / 4 类校验失败显性化 / 权限 (admin 403, 普通员工 403)
  - F12: 行集含零家访者 / 单元格填具体日期 / draft 不计入 / 权限收口
  - 导出: admin 可导 / 普通员工被拒 / 模板 14 列

⚠️ 本文件**不使用根 conftest 的 db 固件** (它走 SessionLocal, 直连开发库 taizhang.db)。
   审计报告 §6.6 已登记这个问题: 每次跑测试都会往开发库写数据, 失败时残留会累积
   (本仓库此前已积了 74 条家访残留 + 8 条演练残留)。
   这里用同名 db 固件遮蔽它 —— 模块内固件优先级高于 conftest, 并配合
   dependency_overrides 把 API 请求也打到同一个临时库。这样:
     - 不会污染开发库, 不需要任何"事后删残留"的清理代码
     - 断言可以依赖全库基数 (库是干净的)
   其余测试文件仍走开发库, 那是待排期的系统性问题, 不在本文件范围内。
"""
import io
import random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import Base
from app.main import app
from app.portrait import models as pmodels  # noqa: F401 触发 ORM 注册

client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --------------------------------------------------------------------- 隔离数据库
# 重构方案 Phase 1.1: 本文件原来自带内存库隔离 shim (换 session_mod/deps 两处
# SessionLocal)。根 tests/conftest.py 已推广同款隔离 (并额外换掉 logger.py 的
# 按值绑定, 修掉了本文件此前打日志时写穿到真实库的隐患), 模块级 shim 随之拆除,
# 用户固件改为 function 级以匹配根 db 固件 —— 每个用例拿全新空库, ehr 唯一约束
# 天然满足, 无需再为"同一会话只能建一次"做 session 级缓存。


@pytest.fixture(scope="function")
def admin_user(db: Session) -> models.User:
    """管理员 (走根 conftest 的隔离内存库)"""
    user = models.User(
        username="admin_f11",
        ehr_id="1000001",
        name="测试管理员",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=True,
        department="测试部门",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_token_headers(admin_user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(admin_user.id)})}"}


@pytest.fixture(scope="function")
def normal_user(db: Session) -> models.User:
    """普通员工 = team_id 为 None (本项目里 team_id 非空即组长, 见审计 §1.1)"""
    user = models.User(
        username="normal_f11",
        ehr_id="1000002",
        name="普通员工",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def normal_token_headers(normal_user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(normal_user.id)})}"}


def _random_ehr(db: Session) -> str:
    while True:
        ehr = str(random.randint(3000000, 8999999))
        if not db.query(models.User).filter(models.User.ehr_id == ehr).first():
            return ehr


@pytest.fixture(scope="function")
def team(db: Session):
    t = models.Team(name="F11测试组", department="测试部门")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_user(db: Session, *, ehr_id: str, name: str, team_id=None, superuser=False):
    user = models.User(
        username=f"f11_{ehr_id}",
        ehr_id=ehr_id,
        name=name,
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=superuser,
        team_id=team_id,
        department="测试部门" if team_id else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def leader(db: Session, team):
    """组长 = 该组的 leader_id (决策 1)。

    旧判据是「有 team_id 即组长」, 所以以前只要把人放进组就行;
    判据改成 teams.leader_id 后, 组员不再自动是组长 —— 固件必须显式
    把组长指向 leader, 否则用例会集体变红 (而且是"该红的", 不是误报)。
    """
    u = _make_user(db, ehr_id=_random_ehr(db), name="F11组长", team_id=team.id)
    team.leader_id = u.id
    db.commit()
    db.refresh(team)
    return u


@pytest.fixture(scope="function")
def member(db: Session, team):
    return _make_user(db, ehr_id=_random_ehr(db), name="F11组员", team_id=team.id)


@pytest.fixture(scope="function")
def leader_headers(leader):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(leader.id)})}"}


@pytest.fixture(scope="function")
def member_headers(member):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(member.id)})}"}


def _xlsx(rows: list[dict]) -> bytes:
    import pandas as pd

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _base_row(visited, **overrides) -> dict:
    row = {
        "所属团队": "审核处理团队",
        "被家访人EHR号": visited.ehr_id,
        "被家访人姓名": visited.name,
        "岗位": "客户经理",
        "联系电话": "13800138000",
        "家访年度": 2026,
        "家访时间": "2026-05-12 14:30:00",
        "家访方式": "线下",
        "家访地址": "F11测试地址A",
        "家访人员及岗位": "1.不该被采信，编造岗位",
        "是否已家访": "是",
        "备注": "F11导入备注",
        "序号": 1,
        "家访记录表扫描件": "已提交",
    }
    row.update(overrides)
    return row


def _post_import(rows: list[dict], headers: dict):
    return client.post(
        f"{API_PORTRAIT}/home-visits/import",
        headers=headers,
        files={"file": ("hv.xlsx", _xlsx(rows), XLSX_MIME)},
    )


# ============================================================================ F11
def test_identity_sanity(db: Session, admin_user, admin_token_headers):
    """隔离是否真的生效: 请求侧认出的当前用户必须就是本库里的 admin。

    失败即说明请求读的不是内存库 —— 宁可这条红着, 也不要让后面 10 条用例
    带着错���的身份假设给出看似合理的绿。
    """
    row = (
        db.query(models.User)
        .filter(models.User.id == admin_user.id)
        .first()
    )
    assert row is not None and row.is_superuser, "内存库里没有本用例建的 admin"
    resp = client.get(
        f"{API_PORTRAIT}/home-visits/matrix", headers=admin_token_headers
    )
    assert resp.status_code == 200, resp.text
    ehrs = [r["ehr_id"] for r in resp.json()["rows"]]
    assert admin_user.ehr_id in ehrs, (
        f"请求侧读到的用户集合不含 admin({admin_user.ehr_id}); "
        f"行集={ehrs}; 请求是否落到开发库?"
    )


def test_f11_import_success(db: Session, leader, member, leader_headers):
    """F11: 合法行入库, 且 visitor_info 按导入人重建 (不采信 Excel 第 10 列)"""
    resp = _post_import([_base_row(member)], leader_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 1, body
    assert body["failed_count"] == 0, body

    record = (
        db.query(pmodels.HomeVisitRecord)
        .filter(
            pmodels.HomeVisitRecord.visited_user_id == member.id,
            pmodels.HomeVisitRecord.visitor_user_id == leader.id,
            pmodels.HomeVisitRecord.visit_address == "F11测试地址A",
        )
        .first()
    )
    assert record is not None, "导入的记录未落库"
    # 导入不是审批通道: 必须走 submit → approve
    assert record.status == "draft", record.status
    assert record.team_name == "审核处理团队"
    assert record.scan_status == "已提交", "B.4 第 14 列未写入"
    assert record.contact_phone == "13800138000", "B.4 第 5 列未写入"
    assert record.feedback == "F11导入备注", "B.4 第 12 列未映射到 feedback"
    # 第 10 列 Excel 里写的是编造内容, 必须被忽略并按导入人重建
    assert "编造岗位" not in (record.visitor_info or "")
    assert record.visitor_info == f"1.{leader.name}，测试部门"
    # 4 列不得因 Excel 把 7 位 EHR 读成数字而变成 "1903951.0"
    assert record.visit_date.isoformat() == "2026-05-12"


def test_f11_import_rejects_wrong_team(db: Session, leader, member, leader_headers):
    """B.4 第 1 列「所属团队」是固定值, 填错必须显性失败而不是被后端悄悄改掉"""
    resp = _post_import([_base_row(member, **{"所属团队": "别的组"})], leader_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 0, body
    assert body["failed_count"] == 1, body
    assert "审核处理团队" in body["failed_rows"][0]["reason"]


def test_f11_import_rejects_name_mismatch(db: Session, leader, member, leader_headers):
    """Excel 姓名与系统不符必须失败: 静默以系统为准会让用户以为导的是自己填的那个人"""
    resp = _post_import([_base_row(member, **{"被家访人姓名": "张三"})], leader_headers)
    body = resp.json()
    assert body["success_count"] == 0, body
    assert "姓名与系统不符" in body["failed_rows"][0]["reason"]


def test_f11_import_rejects_year_mismatch(db: Session, leader, member, leader_headers):
    """年度与家访时间年份不一致必须失败, 否则同一条记录会落进两个年度的矩阵"""
    resp = _post_import([_base_row(member, **{"家访年度": 2025})], leader_headers)
    body = resp.json()
    assert body["success_count"] == 0, body
    assert "年份不一致" in body["failed_rows"][0]["reason"]


def test_f11_import_rejects_cross_team(db: Session, leader, leader_headers):
    """跨组被家访人必须拒绝 (与 create_draft 同口径: 仅本组)"""
    other = _make_user(db, ehr_id=_random_ehr(db), name="F11他组员", team_id=None)
    resp = _post_import([_base_row(other)], leader_headers)
    body = resp.json()
    assert body["success_count"] == 0, body
    assert "非同组" in body["failed_rows"][0]["reason"]


def test_f11_import_admin_rejected(db: Session, admin_user, admin_token_headers, member, team):
    """admin 不可导入: 业务规则"谁做家访谁签字", 与 create_draft 一致"""
    in_team = _make_user(
        db, ehr_id=_random_ehr(db), name="F11同组人", team_id=team.id
    )
    resp = _post_import([_base_row(in_team)], admin_token_headers)
    assert resp.status_code == 403, resp.text
    assert "谁做家访谁签字" in resp.json()["detail"]


def test_f11_import_normal_user_rejected(
    db: Session, normal_user, normal_token_headers, team
):
    """普通员工不可导入。

    注意: 本项目里"组长 ≡ team_id 非空"(审计报告 §1.1), 所以"普通员工"只能用
    team_id=None 的 user 来代表 —— 不能拿带组的 member 试, 它在权限上就是组长。
    """
    target = _make_user(db, ehr_id=_random_ehr(db), name="F11目标", team_id=team.id)
    resp = _post_import([_base_row(target)], normal_token_headers)
    assert resp.status_code == 403, resp.text


# ============================================================================ F12
def test_f12_matrix_includes_zero_visit_users(
    db: Session, admin_user, admin_token_headers, leader, member
):
    """F12 行集 = 基准全员: 从未被家访的人必须有一行全空, 否则这张表藏起了最该盯的人"""
    _post_import([_base_row(member)], {"Authorization": f"Bearer {create_access_token({'sub': str(leader.id)})}"})
    # 手动把记录推到 approved, 否则不进统计口径
    db.query(pmodels.HomeVisitRecord).filter(
        pmodels.HomeVisitRecord.visited_user_id == member.id,
        pmodels.HomeVisitRecord.visit_address == "F11测试地址A",
    ).update({"status": "approved"}, synchronize_session=False)
    db.commit()

    # 再建一个从未被家访的人
    never = _make_user(db, ehr_id=_random_ehr(db), name="F11从未被访", team_id=member.team_id)

    body = client.get(
        f"{API_PORTRAIT}/home-visits/matrix", headers=admin_token_headers
    ).json()
    rows = {r["ehr_id"]: r for r in body["rows"]}

    assert member.ehr_id in rows, "被家访的人不在矩阵里"
    assert "2026年" in rows[member.ehr_id]["visited_years"], rows[member.ehr_id]
    assert any(c["value"] for c in rows[member.ehr_id]["cells"]), "被家访者单元格为空"

    assert never.ehr_id in rows, "零家访者被矩阵藏起来了 (正是这张表要盯出来的人)"
    assert rows[never.ehr_id]["visited_years"] == ""
    assert all(c["value"] == "" for c in rows[never.ehr_id]["cells"])


def test_f12_matrix_excludes_draft(db: Session, admin_user, admin_token_headers, leader, member):
    """草稿不进统计: 还没提交的家访不能算已家访"""
    _post_import([_base_row(member)], {"Authorization": f"Bearer {create_access_token({'sub': str(leader.id)})}"})
    body = client.get(
        f"{API_PORTRAIT}/home-visits/matrix", headers=admin_token_headers
    ).json()
    rows = {r["ehr_id"]: r for r in body["rows"]}
    assert rows[member.ehr_id]["visited_years"] == "", "draft 记录被算成了已家访"

    # 关掉 include_pending 后把状态推到 approved, 应该重新计入
    db.query(pmodels.HomeVisitRecord).filter(
        pmodels.HomeVisitRecord.visited_user_id == member.id,
        pmodels.HomeVisitRecord.visit_address == "F11测试地址A",
    ).update({"status": "approved"}, synchronize_session=False)
    db.commit()
    body = client.get(
        f"{API_PORTRAIT}/home-visits/matrix", headers=admin_token_headers
    ).json()
    rows = {r["ehr_id"]: r for r in body["rows"]}
    assert rows[member.ehr_id]["visited_years"] != "", "approved 记录没被计入"


def test_f12_matrix_normal_user_sees_only_self(
    db: Session, normal_user, normal_token_headers, team
):
    """普通员工的矩阵里只应有自己一行 (PRD §13 家访详情仅自己)。

    同上: "普通员工"必须用 team_id=None 的 user, 带组的在本项目里就是组长。
    """
    body = client.get(
        f"{API_PORTRAIT}/home-visits/matrix", headers=normal_token_headers
    ).json()
    ehrs = [r["ehr_id"] for r in body["rows"]]
    assert ehrs == [normal_user.ehr_id], f"普通员工的矩阵里出现了别人的行: {ehrs}"
    assert body["rows"][0]["visited_years"] == "", "普通员工不该被算作已家访"


def test_f12_matrix_team_filter(db: Session, admin_user, admin_token_headers, team):
    """按分组筛选必须真的筛掉别的组 (筛选与渲染要用同一套取值口径)"""
    in_team = _make_user(db, ehr_id=_random_ehr(db), name="F11组内", team_id=team.id)
    body = client.get(
        f"{API_PORTRAIT}/home-visits/matrix",
        params={"team_name": "F11测试组"},
        headers=admin_token_headers,
    ).json()
    assert body, "筛选后矩阵为空"
    assert all(r["team_name"] == "F11测试组" for r in body["rows"])
    assert in_team.ehr_id in [r["ehr_id"] for r in body["rows"]]


# ============================================================================ 导出
def test_export_excel_admin(db: Session, admin_user, admin_token_headers):
    """导出返回 xlsx, 文件名按 §7.2 格式 家访明细表_YYYY-MM-DD_HHmm.xlsx"""
    resp = client.get(f"{API_PORTRAIT}/home-visits/export", headers=admin_token_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == XLSX_MIME
    cd = resp.headers.get("content-disposition", "")
    assert "filename*=UTF-8''" in cd, cd
    # RFC 5987 里中文是百分号编码的, 断言前必须解码, 否则对着一串 %E5%AE%B6 找汉字
    from urllib.parse import unquote

    assert "家访明细表_" in unquote(cd), cd
    # 内容必须是能打开的工作簿
    wb = openpyxl_from(resp.content)
    assert wb is not None and len(wb) > 0, "导出的 xlsx 打不开或没有数据行"


def test_export_excel_normal_user_rejected(db: Session, normal_user, normal_token_headers):
    """§13: 家访批量导出 Excel 普通员工 ❌"""
    resp = client.get(f"{API_PORTRAIT}/home-visits/export", headers=normal_token_headers)
    assert resp.status_code == 403, resp.text


def openpyxl_from(content: bytes):
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content))
    ws = wb.active
    return list(ws.values)


# ============================================================================ 模板
def test_home_visit_template_has_14_columns():
    """F11 模板必须与 B.4 的 14 列一致, 且必填列齐全"""
    resp = client.get(f"{API_PORTRAIT}/templates/excel/home-visit")
    assert resp.status_code == 200, resp.text
    rows = openpyxl_from(resp.content)
    assert len(rows[0]) == 14, f"模板列数应为 14, 实际 {len(rows[0])}: {rows[0]}"