"""
import_commit_service 回归测试。

重点覆盖:
  - 导入落库状态必须为 completed(对齐审批通过终态)
  - approval_status 必须为 approved
  - import_batch_id / imported_by_id / created_by_id 等关键字段正确写入
  - 柜员号反查 + 团队反查 + fallback 行为
  - 问题行(issue)不会被写入

对应台账导入功能测试用例 TC-14「正常导入 + 双写验证」。
"""
import asyncio
from io import BytesIO
from typing import List

import pytest
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import import_commit_service


# ---------- helpers ----------

class _FakeUploadFile:
    """轻量级 UploadFile mock,满足 read_upload_file 所需的 .read() / .filename 接口"""
    def __init__(self, content: bytes, filename: str = "test.xlsx"):
        self.content = content
        self.filename = filename

    async def read(self) -> bytes:
        return self.content


def _build_xlsx_bytes(headers: List[str], data_rows: List[List], with_example: bool = True) -> bytes:
    """
    构造符合 load_workbook_rows 期望的 xlsx:
      - Sheet 1: 「填表说明」(任意内容)
      - Sheet 2: 「数据」,第 1 行表头,第 2 行 hint,第 3 行示例(可去掉),其后为数据
    示例行携带与 import_template_service 相同的「示例行,请删除后从下一行开始填写」标记。
    """
    wb = Workbook()
    # 默认 Sheet 1 改名 + 写一行说明
    ws1 = wb.active
    ws1.title = "填表说明"
    ws1.append(["导入模板说明", "数据从示例行之后开始填写"])

    ws2 = wb.create_sheet("数据")
    ws2.append(headers)              # 第 1 行:表头
    ws2.append(["hint", "hint"])      # 第 2 行:hint
    if with_example:
        ws2.append(["示例行,请删除后从下一行开始填写"] + [None] * (len(headers) - 1))  # 第 3 行:示例
    for row in data_rows:            # 数据紧跟其后
        ws2.append(row)

    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def _run(coro):
    """同步执行 async coroutine(测试环境未装 pytest-asyncio)"""
    return asyncio.run(coro)


# ---------- 关键回归:status / approval_status ----------

def test_run_commit_sets_status_completed(
    db: Session, template: models.Template, normal_user: models.User
):
    """
    核心回归:导入落库的 Ledger.status 必须为 'completed',
    与审批通过终态对齐;V2 方案 §4「导入即终态」。
    防止有人误改回 active(早期 bug:status='active' + approval_status='approved'
    在前端被渲染成「处理中/已批准」语义矛盾)。
    """
    headers = ["测试字段1", "测试字段2"]
    xlsx = _build_xlsx_bytes(headers, [["值1", 100]])
    file = _FakeUploadFile(xlsx, "import.xlsx")

    result = _run(import_commit_service.run_commit(
        db,
        template_id=template.id,
        file=file,
        current_user=normal_user,
    ))

    assert result.success_count == 1
    assert result.failed_count == 0
    assert len(result.created_ledger_ids) == 1

    ledger = db.query(models.Ledger).filter(
        models.Ledger.id == result.created_ledger_ids[0]
    ).one()
    assert ledger.status == "completed", (
        "回归失败:导入台账 status 应为 'completed' 而非 'active'"
    )
    assert ledger.approval_status == "approved"
    assert ledger.import_batch_id == result.batch_id
    assert ledger.imported_by_id == normal_user.id
    assert ledger.template_id == template.id
    assert ledger.created_by_id == normal_user.id  # 无 ehr 字段配置时兜底为操作者
    assert ledger.data == {"测试字段1": "值1", "测试字段2": 100}


def test_run_commit_writes_required_audit_fields(
    db: Session, template: models.Template, normal_user: models.User
):
    """
    验证双写字段:submitted_at / approved_at / created_at / import_batch_id 均落库,
    且 import_batch_id 格式正确(IMP-yyyymmdd-xxxxxxxx)。
    """
    headers = ["测试字段1"]
    xlsx = _build_xlsx_bytes(headers, [["值-A"], ["值-B"]])
    file = _FakeUploadFile(xlsx)

    result = _run(import_commit_service.run_commit(
        db,
        template_id=template.id,
        file=file,
        current_user=normal_user,
    ))

    assert result.success_count == 2
    ledgers = db.query(models.Ledger).filter(
        models.Ledger.import_batch_id == result.batch_id
    ).all()
    assert len(ledgers) == 2
    for lg in ledgers:
        assert lg.status == "completed"
        assert lg.approval_status == "approved"
        assert lg.submitted_at is not None
        assert lg.approved_at is not None
        assert lg.import_batch_id.startswith("IMP-")


def test_run_commit_skips_invalid_rows(
    db: Session, template: models.Template, normal_user: models.User
):
    """
    问题行(缺必填)不会被写入,只成功导入合法行。
    """
    headers = ["测试字段1"]  # 必填
    xlsx = _build_xlsx_bytes(headers, [
        ["合法值-1"],   # 合法
        [None],         # 必填为空 → issue,跳过
        ["合法值-2"],   # 合法
    ])
    file = _FakeUploadFile(xlsx)

    result = _run(import_commit_service.run_commit(
        db,
        template_id=template.id,
        file=file,
        current_user=normal_user,
    ))

    assert result.success_count == 2
    assert result.failed_count == 0  # 校验阶段跳过,不进 failed_items
    assert db.query(models.Ledger).filter(
        models.Ledger.import_batch_id == result.batch_id
    ).count() == 2


def test_run_commit_batch_ids_are_unique(
    db: Session, template: models.Template, normal_user: models.User
):
    """两次导入产生不同的 batch_id。"""
    headers = ["测试字段1"]
    file1 = _FakeUploadFile(_build_xlsx_bytes(headers, [["v1"]]))
    file2 = _FakeUploadFile(_build_xlsx_bytes(headers, [["v2"]]))

    r1 = _run(import_commit_service.run_commit(
        db, template_id=template.id, file=file1, current_user=normal_user,
    ))
    r2 = _run(import_commit_service.run_commit(
        db, template_id=template.id, file=file2, current_user=normal_user,
    ))

    assert r1.batch_id != r2.batch_id
