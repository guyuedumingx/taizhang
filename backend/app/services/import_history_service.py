"""
导入历史服务:按批次聚合查询 ledgers.import_batch_id。

数据来源:
  - batch 元信息从 system_logs 里取(action=import, resource_id=batch_id)
  - 成功/失败计数从 ledgers 表按 import_batch_id 聚合
  - 失败明细 import_failed_items 是 commit 时记录的,当前版本不入库(简化),
    仅在 commit 响应和 failures xlsx 下载里返回
"""
import io
from typing import List, Optional

from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


def list_import_history(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
) -> schemas.ImportHistoryList:
    """按批次聚合列出导入历史(按 import_batch_id 分组)"""
    # 批次列表:以 ledgers 表里出现过的 import_batch_id 为准
    batch_rows = (
        db.query(
            models.Ledger.import_batch_id,
            func.min(models.Ledger.template_id).label("template_id"),
            func.count(models.Ledger.id).label("success_count"),
            func.min(models.Ledger.created_at).label("imported_at"),
            func.min(models.Ledger.imported_by_id).label("imported_by_id"),
        )
        .filter(models.Ledger.import_batch_id.isnot(None))
        .group_by(models.Ledger.import_batch_id)
        .order_by(func.min(models.Ledger.created_at).desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = (
        db.query(models.Ledger.import_batch_id)
        .filter(models.Ledger.import_batch_id.isnot(None))
        .distinct()
        .count()
    )

    # 批量取模板名 + 导入者名,避免 N+1
    template_ids = {r.template_id for r in batch_rows if r.template_id}
    templates = {
        t.id: t.name
        for t in db.query(models.Template).filter(models.Template.id.in_(template_ids)).all()
    } if template_ids else {}

    user_ids = {r.imported_by_id for r in batch_rows if r.imported_by_id}
    users = {
        u.id: u.name or u.username
        for u in db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    } if user_ids else {}

    # 每个批次对应的 system_logs 详情(filename, failed_count)
    batch_ids = [r.import_batch_id for r in batch_rows]
    logs = {
        log.resource_id: log
        for log in db.query(models.SystemLog)
        .filter(
            models.SystemLog.action == models.LogAction.IMPORT,
            models.SystemLog.resource_id.in_(batch_ids),
        )
        .all()
    } if batch_ids else {}

    items: List[schemas.ImportHistoryItem] = []
    for r in batch_rows:
        log = logs.get(r.import_batch_id)
        filename = None
        failed_count = 0
        if log and log.details:
            filename = log.details.get("filename")
            failed_count = log.details.get("failed_count") or 0

        items.append(schemas.ImportHistoryItem(
            batch_id=r.import_batch_id,
            template_id=r.template_id or 0,
            template_name=templates.get(r.template_id, "未知模板"),
            imported_by_id=r.imported_by_id or 0,
            imported_by_name=users.get(r.imported_by_id),
            imported_at=r.imported_at,
            total_rows=(r.success_count or 0) + failed_count,
            success_count=r.success_count or 0,
            failed_count=failed_count,
            filename=filename,
        ))

    return schemas.ImportHistoryList(total=total, items=items)


def get_import_history_detail(
    db: Session,
    *,
    batch_id: str,
) -> schemas.ImportHistoryDetail:
    """单批次详情(含台账 ID 列表)"""
    ledgers = (
        db.query(models.Ledger)
        .filter(models.Ledger.import_batch_id == batch_id)
        .all()
    )
    if not ledgers:
        raise HTTPException(status_code=404, detail="批次不存在或已被清空")

    template_id = ledgers[0].template_id
    template_name = ledgers[0].template.name if ledgers[0].template else "未知模板"
    imported_by_id = ledgers[0].imported_by_id or 0
    imported_by_name = (
        (ledgers[0].imported_by.name or ledgers[0].imported_by.username)
        if ledgers[0].imported_by else None
    )
    imported_at = min(l.created_at for l in ledgers if l.created_at)

    log = (
        db.query(models.SystemLog)
        .filter(
            models.SystemLog.action == models.LogAction.IMPORT,
            models.SystemLog.resource_id == batch_id,
        )
        .first()
    )
    filename = None
    failed_count = 0
    if log and log.details:
        filename = log.details.get("filename")
        failed_count = log.details.get("failed_count") or 0

    return schemas.ImportHistoryDetail(
        batch_id=batch_id,
        template_id=template_id or 0,
        template_name=template_name,
        imported_by_id=imported_by_id,
        imported_by_name=imported_by_name,
        imported_at=imported_at,
        total_rows=len(ledgers) + failed_count,
        success_count=len(ledgers),
        failed_count=failed_count,
        filename=filename,
        created_ledger_ids=[l.id for l in ledgers],
        failed_items=[],
    )


def build_failures_xlsx(
    db: Session,
    *,
    batch_id: str,
) -> bytes:
    """
    生成失败清单 xlsx。
    当前版本失败明细未入 DB(简化),从 system_logs.details 里取;
    若 details 没有 failed_items,则返回空表(只列批次号)。
    """
    log = (
        db.query(models.SystemLog)
        .filter(
            models.SystemLog.action == models.LogAction.IMPORT,
            models.SystemLog.resource_id == batch_id,
        )
        .first()
    )
    failed_items: List[dict] = []
    if log and log.details:
        failed_items = log.details.get("failed_items") or []

    wb = Workbook()
    ws = wb.active
    ws.title = "失败清单"
    ws.append(["批次号", "行号", "字段", "原始值", "失败原因"])
    for item in failed_items:
        ws.append([
            batch_id,
            item.get("row"),
            item.get("field") or "",
            str(item.get("raw") or ""),
            item.get("reason") or "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
