"""台账导入相关 endpoints

覆盖:
  - GET  /ledgers/import-template/{template_id}         下载导入模板
  - GET  /ledgers/import-configs                        列出导入配置
  - POST /ledgers/import-configs/reload                 热重载导入配置
  - POST /ledgers/import/validate                       预校验(不落库)
  - POST /ledgers/import/commit                         确认导入(落库)
  - GET  /ledgers/import/history                        导入历史列表
  - GET  /ledgers/import/history/{batch_id}             单批次详情
  - GET  /ledgers/import/history/{batch_id}/failures    单批次失败清单 xlsx

所有端点要求当前用户具备 ledger:import 权限。
"""
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core import import_config_loader
from app.db.session import get_db
from app.services import (
    import_commit_service,
    import_history_service,
    import_template_service,
    import_validation_service,
)

router = APIRouter()


def _require_import_permission(current_user: models.User) -> None:
    """复用 deps.check_permissions 的 superuser 短路 + casbin 校验"""
    if not deps.check_permissions("ledger", "import", current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有台账导入权限(需要 ledger:import)",
        )


@router.get("/import-template/{template_id}")
def download_import_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """下载指定模板的导入 Excel(双 Sheet:填表说明 + 模板)"""
    _require_import_permission(current_user)
    content = import_template_service.generate_import_template(db, template_id)
    filename = f"import_template_{template_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/import-configs", response_model=schemas.ImportConfigList)
def list_import_configs(
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """列出当前生效的导入配置"""
    _require_import_permission(current_user)
    raw_configs = import_config_loader.get_import_configs()
    configs = [schemas.ImportConfig(**cfg) for cfg in raw_configs]
    return schemas.ImportConfigList(configs=configs)


@router.post("/import-configs/reload")
def reload_import_configs(
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """热重载 ledger_import_config.json"""
    _require_import_permission(current_user)
    count = import_config_loader.reload()
    return {"message": "导入配置已重载", "count": count}


@router.post("/import/validate", response_model=schemas.ImportValidationReport)
async def validate_import(
    template_id: int = Form(...),
    file: UploadFile = File(...),
    team_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """预校验上传的 Excel,不落库,返回校验报告"""
    _require_import_permission(current_user)
    return await import_validation_service.run_validation(
        db, template_id=template_id, file=file, fallback_team_id=team_id,
    )


@router.post("/import/commit", response_model=schemas.ImportCommitResult)
async def commit_import(
    template_id: int = Form(...),
    file: UploadFile = File(...),
    team_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """确认导入:服务端二次校验后落库,返回批次结果"""
    _require_import_permission(current_user)
    return await import_commit_service.run_commit(
        db,
        template_id=template_id,
        file=file,
        current_user=current_user,
        fallback_team_id=team_id,
        filename=file.filename,
    )


@router.get("/import/history", response_model=schemas.ImportHistoryList)
def list_import_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """按批次聚合列出导入历史"""
    _require_import_permission(current_user)
    return import_history_service.list_import_history(db, skip=skip, limit=limit)


@router.get("/import/history/{batch_id}", response_model=schemas.ImportHistoryDetail)
def get_import_history_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """单批次详情(含台账 ID 列表)"""
    _require_import_permission(current_user)
    return import_history_service.get_import_history_detail(db, batch_id=batch_id)


@router.get("/import/history/{batch_id}/failures")
def download_import_failures(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """下载单批次失败清单 xlsx"""
    _require_import_permission(current_user)
    content = import_history_service.build_failures_xlsx(db, batch_id=batch_id)
    filename = f"import_failures_{batch_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
