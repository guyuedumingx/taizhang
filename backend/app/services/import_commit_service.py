"""
提交写入服务:二次校验 + 批量写入 Ledger + 记录 system_logs。

关键设计:
  - 复用 import_validation_service 的解析+校验,保证 validate 与 commit 逻辑一致
  - 以服务端二次校验结果为准,importable 行才写入
  - 每 200 行 commit 一次,失败行记入 failed_items 不阻断后续
  - 写入字段:
      data        = 原始行值(不做清洗落库)
      name        = name_field → data.name → import-{template}-{seq}
      status      = active
      approval_status = approved
      team_id     = identity_mapping 反查(失败用 fallback_team_id)
      created_by_id = 柜员号反查(失败兜底当前操作者)
      updated_by_id = created_by_id
      imported_by_id = 当前操作者
      import_batch_id = 本次批次 UUID
  - 不可编辑/不可删除/不可撤回(沿用现有 update_ledger / delete_ledger 限制)
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import import_config_loader
from app.services import import_validation_service

logger = logging.getLogger(__name__)

COMMIT_BATCH_SIZE = 200


def _field_label(field: models.Field) -> str:
    return field.label or field.name


def _generate_batch_id() -> str:
    return f"IMP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def _resolve_name(
    row_values: Dict[str, Any],
    *,
    name_field: Optional[str],
    template_name: str,
    seq: int,
) -> str:
    if name_field and row_values.get(name_field) is not None:
        return str(row_values[name_field])
    if row_values.get("name") is not None:
        return str(row_values["name"])
    safe_template = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in template_name)
    return f"import-{safe_template}-{seq:05d}"


async def run_commit(
    db: Session,
    *,
    template_id: int,
    file: UploadFile,
    current_user: models.User,
    fallback_team_id: Optional[int] = None,
    filename: Optional[str] = None,
) -> schemas.ImportCommitResult:
    """commit 端点入口"""
    start_time = time.time()

    template = crud.template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    cfg = import_config_loader.get_import_config_for_template(template.name) or {}

    # 行数硬上限提前拦截
    content = await import_validation_service.read_upload_file(file)
    headers, rows = import_validation_service.load_workbook_rows(content)
    hard_limit = int(cfg.get("max_rows_hard_limit") or 5000)
    if len(rows) > hard_limit:
        raise HTTPException(
            status_code=400,
            detail=f"总行数 {len(rows)} 超过硬上限 {hard_limit},请拆分文件后分批导入",
        )

    # 二次校验(与 validate 同一套逻辑)
    existing_keys = crud.ledger.get_existing_unique_keys(
        db,
        template_id=template.id,
        key_fields=[k for k in (cfg.get("unique_keys") or ["name"]) if k != "name"],
    )
    report = import_validation_service.validate_rows(
        db,
        template=template,
        cfg=cfg,
        rows=rows,
        existing_keys=existing_keys,
        fallback_team_id=fallback_team_id,
    )

    batch_id = _generate_batch_id()
    name_field: Optional[str] = cfg.get("name_field")
    identity_team_field = import_config_loader.get_identity_field(cfg, "team")
    identity_user_field = import_config_loader.get_identity_field(cfg, "created_by")

    # 预加载映射
    teams = {t.name: t.id for t in db.query(models.Team).all()}
    users_by_ehr = {u.ehr_id: u.id for u in db.query(models.User).all()
                    if getattr(u, "ehr_id", None)}

    # importable 行集合(校验无 issue 的行)
    issue_rows = {issue.row for issue in report.issues if issue.row > 0}
    importable = [r for r in rows if r["_row"] not in issue_rows]

    created_ids: List[int] = []
    failed_items: List[schemas.ImportFailedItem] = []

    now = datetime.now()
    seq = 0

    for row_data in importable:
        seq += 1
        excel_row: int = row_data["_row"]
        row_values: Dict[str, Any] = {k: v for k, v in row_data.items() if k != "_row"}

        try:
            # 归属反查(此时应已成功,若仍失败则跳过)
            team_id: Optional[int] = None
            if identity_team_field:
                team_name = row_values.get(identity_team_field)
                if team_name is not None:
                    team_id = teams.get(str(team_name))
                    if team_id is None:
                        team_id = fallback_team_id
            if team_id is None and fallback_team_id is not None:
                team_id = fallback_team_id

            # created_by 反查,失败兜底为当前操作者
            created_by_id = current_user.id
            if identity_user_field:
                ehr_value = row_values.get(identity_user_field)
                if ehr_value is not None:
                    resolved = users_by_ehr.get(str(ehr_value).strip())
                    if resolved is not None:
                        created_by_id = resolved

            ledger_name = _resolve_name(
                row_values, name_field=name_field,
                template_name=template.name, seq=seq,
            )

            ledger_obj = models.Ledger(
                name=ledger_name,
                description=None,
                status="active",
                approval_status="approved",
                team_id=team_id,
                template_id=template.id,
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
                imported_by_id=current_user.id,
                import_batch_id=batch_id,
                data=row_values,
                created_at=now,
                updated_at=now,
                submitted_at=now,
                approved_at=now,
            )
            db.add(ledger_obj)
            db.flush()  # 拿 id,但不 commit
            created_ids.append(ledger_obj.id)

            # 分批 commit
            if len(created_ids) % COMMIT_BATCH_SIZE == 0:
                db.commit()

        except Exception as exc:
            db.rollback()
            failed_items.append(schemas.ImportFailedItem(
                row=excel_row,
                field=None,
                raw=None,
                reason=f"写入失败: {exc}",
            ))

    # 最终 commit
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"导入提交失败: {exc}")

    elapsed = round(time.time() - start_time, 2)
    failed_count = len(failed_items)

    # 写 system_logs
    try:
        log_entry = models.SystemLog(
            user_id=current_user.id,
            level=models.LogLevel.INFO,
            module="ledger",
            action=models.LogAction.IMPORT,
            resource_type="ledger_import",
            resource_id=batch_id,
            message=f"导入批次 {batch_id} 成功 {len(created_ids)} 条,失败 {failed_count} 条",
            details={
                "import_batch_id": batch_id,
                "template_id": template.id,
                "template_name": template.name,
                "filename": filename,
                "success_count": len(created_ids),
                "failed_count": failed_count,
                "total_rows": report.total_rows,
                # 失败明细同时落 system_logs.details,供 history/{batch_id}/failures 下载
                "failed_items": [
                    {"row": f.row, "field": f.field, "raw": f.raw, "reason": f.reason}
                    for f in failed_items
                ],
            },
            created_at=now,
        )
        db.add(log_entry)
        db.commit()
    except Exception as exc:
        logger.error(f"写入导入日志失败(batch_id={batch_id}): {exc}")
        db.rollback()

    failures_url = None
    if failed_count > 0:
        failures_url = f"/api/v1/ledgers/import/history/{batch_id}/failures"

    return schemas.ImportCommitResult(
        batch_id=batch_id,
        template_id=template.id,
        template_name=template.name,
        success_count=len(created_ids),
        failed_count=failed_count,
        elapsed_seconds=elapsed,
        created_ledger_ids=created_ids,
        failed_items=failed_items,
        failures_download_url=failures_url,
    )
