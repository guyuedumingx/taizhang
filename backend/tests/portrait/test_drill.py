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


def test_drill_baseline(db: Session, admin_user, normal_token_headers):
    """基线: 列表 + 矩阵可访问 (普通用户只读)"""
    resp = client.get(f"{API_PORTRAIT}/drills", headers=normal_token_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body and "total" in body

    resp = client.get(f"{API_PORTRAIT}/drills/matrix", headers=normal_token_headers)
    assert resp.status_code == 200, resp.text
    matrix = resp.json()
    assert matrix["total_drills"] == 0
    assert matrix["rows"] == []


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

    matrix = client.get(f"{API_PORTRAIT}/drills/matrix", headers=admin_token_headers).json()
    assert matrix["total_drills"] == 2
    assert len(matrix["columns"]) == 2

    # 找到 admin 对应的行
    row = next(r for r in matrix["rows"] if r["ehr_id"] == admin_user.ehr_id)
    assert row["participated_count"] == 2
    assert all(c["participated"] for c in row["cells"])
    assert len(row["cells"]) == 2

    # 清理
    client.delete(f"{API_PORTRAIT}/drills/{drill2['id']}", headers=admin_token_headers)
    client.delete(f"{API_PORTRAIT}/drills/{drill1['id']}", headers=admin_token_headers)


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
