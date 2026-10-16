"""
portrait 消防演练 F2-F4 测试 (阶段 D)

覆盖:
  - 基线: 健康 / 列表 / 矩阵 (3 test)
  - F2 演练登记 (admin 可, 普通用户被拒) + 无效 EHR 显性报错 (2 test)
  - F4 参与矩阵行/列/计数正确性 (1 test)
  - F3 批量导入 (有效 EHR 入库 + 无效 EHR 进 failed_rows, Rule 12) (1 test)
"""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.main import app
from app.portrait import models as pmodels

client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"
# 说明: 测试已通过 tests/conftest.py 的 dependency_overrides 走独立内存库,
# 无需再手动清理演练数据 (原先清理会残留孤儿参与者行)。


def test_drill_baseline(db: Session, admin_user, normal_user, normal_token_headers):
    """基线: 列表 + 矩阵可访问 (普通用户只读)

    矩阵行集 2026-10-14 起改为「基准全员」(附录 B.1)。普通员工可见范围收口到
    仅自己 (PRD §13), 因此即使一场演练都没有, 也应有自己那一行 (全 0)。
    """
    resp = client.get(f"{API_PORTRAIT}/drills", headers=normal_token_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body and "total" in body

    resp = client.get(f"{API_PORTRAIT}/drills/matrix", headers=normal_token_headers)
    assert resp.status_code == 200, resp.text
    matrix = resp.json()
    assert matrix["total_drills"] == 0
    # 普通员工只能看到自己这一行, 不应看到别人
    assert [r["ehr_id"] for r in matrix["rows"]] == [normal_user.ehr_id]
    assert matrix["rows"][0]["participated_count"] == 0
    assert matrix["total_participants"] == 0


def test_drill_create_admin_only(db: Session, admin_user, admin_token_headers, normal_token_headers):
    """F2: 普通用户被拒, admin 可登记; 无效 EHR 显性报错"""
    # 普通用户登记 -> 403
    resp = client.post(
        f"{API_PORTRAIT}/drills",
        headers=normal_token_headers,
        json={
            "activity_date": "2026-05-12",
            "drill_type": "应急疏散",
            "location": "总行 1 楼大厅",
            "participant_ehr_ids": [admin_user.ehr_id],
        },
    )
    assert resp.status_code == 403, resp.text

    # admin 登记 (含有效 EHR)
    resp = client.post(
        f"{API_PORTRAIT}/drills",
        headers=admin_token_headers,
        json={
            "activity_date": "2026-05-12",
            "drill_type": "应急疏散",
            "location": "总行 1 楼大厅",
            "participant_ehr_ids": [admin_user.ehr_id],
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["participant_count"] == 1

    # 无效 EHR -> 400 且带原因 (Rule 12)
    resp = client.post(
        f"{API_PORTRAIT}/drills",
        headers=admin_token_headers,
        json={
            "activity_date": "2026-05-13",
            "drill_type": "演练",
            "location": "操场",
            "participant_ehr_ids": ["9999999"],  # 不存在的 EHR
        },
    )
    assert resp.status_code == 400, resp.text
    assert "无效参与人员" in resp.json()["detail"]

    # 清理: 删除创建的记录
    client.delete(f"{API_PORTRAIT}/drills/{created['id']}", headers=admin_token_headers)


def test_drill_matrix_rows_and_counts(db: Session, admin_user, admin_token_headers):
    """F4: 矩阵行/列/参与计数正确"""
    # 两场演练, 均含 admin 参与
    resp1 = client.post(
        f"{API_PORTRAIT}/drills",
        headers=admin_token_headers,
        json={
            "activity_date": "2026-05-12",
            "drill_type": "应急疏散",
            "location": "A楼",
            "participant_ehr_ids": [admin_user.ehr_id],
        },
    )
    resp2 = client.post(
        f"{API_PORTRAIT}/drills",
        headers=admin_token_headers,
        json={
            "activity_date": "2026-06-01",
            "drill_type": "消防培训",
            "location": "B楼",
            "participant_ehr_ids": [admin_user.ehr_id],
        },
    )
    drill1 = resp1.json()
    drill2 = resp2.json()

    # 断言只针对本用例自己创建的两列, 不断言全库基数。
    # 理由: 测试直接写开发库 (conftest 的 db fixture 走 SessionLocal), 库里的演练
    # 记录数取决于历史上跑过几次、失败过几次 —— 断言 total_drills==2 必然在有残留时
    # 失败, 而删残留不是测试该做的事 (清理逻辑必须在 try/finally 里, 不能靠事后删库)。
    matrix = client.get(f"{API_PORTRAIT}/drills/matrix", headers=admin_token_headers).json()
    col_index = {c["drill_id"]: i for i, c in enumerate(matrix["columns"])}
    assert drill1["id"] in col_index, "本用例创建的演练 1 未出现在矩阵列中"
    assert drill2["id"] in col_index, "本用例创建的演练 2 未出现在矩阵列中"

    row = next(r for r in matrix["rows"] if r["ehr_id"] == admin_user.ehr_id)
    assert row["cells"][col_index[drill1["id"]]]["participated"] is True
    assert row["cells"][col_index[drill2["id"]]]["participated"] is True
    # 单元格数必须与列数一一对应
    assert len(row["cells"]) == len(matrix["columns"])

    # 清理
    client.delete(f"{API_PORTRAIT}/drills/{drill2['id']}", headers=admin_token_headers)
    client.delete(f"{API_PORTRAIT}/drills/{drill1['id']}", headers=admin_token_headers)


def test_drill_read_permission_isolated_by_viewer(
    db: Session, admin_user, normal_user, admin_token_headers, normal_token_headers
):
    """回归: viewer 参数不得空转。

    此前 list_records / get_detail / matrix 三个函数都声明了 viewer 却从未使用,
    三处全表直查 —— 任意登录员工可见全部演练记录、全部参与人、全公司矩阵。
    PRD §13 要求: 员工仅自己 / 组长本组 / 管理员全员。

    normal_user 的 team_id 为 NULL (create_random_user 不设组), 因此只能看到
    自己参与过的演练; admin 参与而 normal_user 未参与的演练对他不可见。
    """
    # admin 参与的一场演练 (normal_user 不参与)
    # 创建必须放进 try: 断言失败时也要清理, 否则残留数据会污染同文件其他用例
    # (tests 共用 test_services.db, test_drill_matrix_rows_and_counts 断言总数=2)
    drill = None
    try:
        resp = client.post(
            f"{API_PORTRAIT}/drills",
            headers=admin_token_headers,
            json={
                "activity_date": "2026-07-01",
                "drill_type": "应急疏散",
                "location": "C楼",
                "participant_ehr_ids": [admin_user.ehr_id],
            },
        )
        assert resp.status_code == 201, resp.text
        drill = resp.json()
        # 列表: 普通员工看不到不属于自己的演练
        listed = client.get(f"{API_PORTRAIT}/drills", headers=normal_token_headers)
        assert listed.status_code == 200, listed.text
        assert drill["id"] not in [i["id"] for i in listed.json()["items"]], \
            "普通员工看到了自己未参与的演练"

        # 详情: 不可见走 404 而非 403, 不泄露"该演练是否存在"
        detail = client.get(
            f"{API_PORTRAIT}/drills/{drill['id']}", headers=normal_token_headers
        )
        assert detail.status_code == 404, detail.text

        # 矩阵: 列(演练)与行(员工)都不得出现 admin / 该演练
        matrix = client.get(f"{API_PORTRAIT}/drills/matrix", headers=normal_token_headers)
        assert matrix.status_code == 200, matrix.text
        body = matrix.json()
        assert drill["id"] not in [c["drill_id"] for c in body["columns"]], \
            "普通员工的矩阵里出现了自己未参与的演练"
        assert admin_user.ehr_id not in [r["ehr_id"] for r in body["rows"]], \
            "普通员工的矩阵里出现了别人的行"

        # 管理员仍然全员可见
        admin_list = client.get(f"{API_PORTRAIT}/drills", headers=admin_token_headers)
        assert drill["id"] in [i["id"] for i in admin_list.json()["items"]], \
            "管理员反而看不到本该可见的演练"
    finally:
        if drill is not None:
            client.delete(
                f"{API_PORTRAIT}/drills/{drill['id']}", headers=admin_token_headers
            )


def test_drill_import_reports_failures(db: Session, admin_user, admin_token_headers):
    """F3 批量导入: 有效 EHR 入库, 无效 EHR 进 failed_rows"""
    import pandas as pd
    import io

    df = pd.DataFrame([
        {"活动日期": "2026-07-01", "演练类型": "演练", "地点": "操场",
         "EHR号": admin_user.ehr_id, "姓名": admin_user.name, "是否参与": "是"},
        {"活动日期": "2026-07-01", "演练类型": "演练", "地点": "操场",
         "EHR号": "9999999", "姓名": "不存在", "是否参与": "是"},
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)

    resp = client.post(
        f"{API_PORTRAIT}/drills/import",
        headers=admin_token_headers,
        files={"file": ("drill.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 1
    assert body["failed_count"] == 1
    assert any(f["ehr_id"] == "9999999" for f in body["failed_rows"])
    assert any("不存在" in f["reason"] for f in body["failed_rows"])  # Rule 12 显性原因

    # 清理: 删掉导入创建的活动及其参与记录
    record = db.query(pmodels.DrillRecord).filter(
        pmodels.DrillRecord.activity_date == date(2026, 7, 1)
    ).first()
    if record:
        client.delete(f"{API_PORTRAIT}/drills/{record.id}", headers=admin_token_headers)
