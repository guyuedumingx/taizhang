"""
import_validation_service 回归测试。

重点覆盖:
  - load_workbook_rows 对「示例行已删除」的兼容(数据丢失 bug 回归:
    模板说明让用户删示例行,旧解析器盲跳前 3 行会把首条数据吞掉)
  - 团队兜底 fallback_notice 的生成(兜底生效时可感知)
"""
from sqlalchemy.orm import Session

from app import models
from app.services.import_validation_service import (
    load_workbook_rows,
    validate_rows,
)

from .test_import_commit_service import _build_xlsx_bytes


# ---------- 解析:示例行存在 / 已删除 ----------

def test_load_workbook_rows_with_example_row():
    """示例行未删(标准形态):数据从第 4 行起。"""
    xlsx = _build_xlsx_bytes(["字段1", "字段2"], [["a", 1], ["b", 2]])
    headers, rows = load_workbook_rows(xlsx)
    assert headers == ["字段1", "字段2"]
    assert [r["_row"] for r in rows] == [4, 5]
    assert rows[0]["字段1"] == "a"


def test_load_workbook_rows_example_deleted():
    """
    回归:用户按模板说明删除了示例行 → 首条数据上移到第 3 行,
    必须被解析(旧行为:盲跳 3 行,首条数据被静默吞掉)。
    """
    xlsx = _build_xlsx_bytes(["字段1", "字段2"], [["a", 1], ["b", 2]], with_example=False)
    headers, rows = load_workbook_rows(xlsx)
    assert headers == ["字段1", "字段2"]
    assert [r["_row"] for r in rows] == [3, 4]
    assert rows[0]["字段1"] == "a"
    assert rows[1]["字段2"] == 2


# ---------- 团队兜底提示 ----------

def _make_cfg() -> dict:
    return {
        "unique_keys": ["流水号"],
        "name_field": "流水号",
        "identity_mapping": {"team": "组别", "created_by": "柜员号"},
    }


def test_fallback_notice_when_team_unresolvable(
    db: Session, template: models.Template, team: models.Team
):
    """选了兜底团队:组别反查失败的行静默归入,但要生成 fallback_notice。"""
    rows = [
        {"_row": 3, "测试字段1": "a", "流水号": "T1", "组别": "不存在的团队", "柜员号": None},
        {"_row": 4, "测试字段1": "b", "流水号": "T2", "组别": "不存在的团队", "柜员号": None},
    ]
    report = validate_rows(
        db, template=template, cfg=_make_cfg(), rows=rows,
        existing_keys={}, fallback_team_id=team.id,
    )
    # 兜底生效 → 不报团队问题
    assert not [i for i in report.issues if i.type == "team_not_found"]
    # 但有提示,且含团队名与行数
    assert report.fallback_notice is not None
    assert team.name in report.fallback_notice
    assert "2 行" in report.fallback_notice
    assert report.total_rows == 2
    assert report.importable_count == 2


def test_no_fallback_notice_without_fallback_or_when_all_resolve(
    db: Session, template: models.Template, team: models.Team
):
    """没选兜底 → 报团队问题、无提示;组别全部可解析 → 也无提示。"""
    rows_bad = [{"_row": 3, "测试字段1": "a", "流水号": "T1", "组别": "不存在的团队", "柜员号": None}]
    report = validate_rows(
        db, template=template, cfg=_make_cfg(), rows=rows_bad,
        existing_keys={}, fallback_team_id=None,
    )
    assert [i.type for i in report.issues] == ["team_not_found"]
    assert report.fallback_notice is None

    rows_ok = [{"_row": 3, "测试字段1": "a", "流水号": "T1", "组别": team.name, "柜员号": None}]
    report2 = validate_rows(
        db, template=template, cfg=_make_cfg(), rows=rows_ok,
        existing_keys={}, fallback_team_id=team.id,
    )
    assert report2.issues == []
    assert report2.fallback_notice is None
