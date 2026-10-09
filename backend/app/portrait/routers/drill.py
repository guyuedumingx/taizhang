"""portrait 消防演练路由 (PRD §10.2 F2-F4)。"""
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait.schemas import drill as drill_schema
from app.portrait.services import drill_service

router = APIRouter()


def _require_admin(current_user: models.User) -> None:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


def _serialize(record) -> dict:
    return {
        "id": record.id,
        "activity_date": record.activity_date,
        "drill_type": record.drill_type,
        "location": record.location,
        "duration_minutes": record.duration_minutes,
        "participant_count": getattr(record, "_participant_count", 0),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@router.get("", summary="F2/F3 消防演练列表")
def list_drills(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    drill_type: Optional[str] = Query(None),
    team_name: Optional[str] = Query(None),
):
    items, total = drill_service.drill_service.list_records(
        db, viewer=current_user, skip=skip, limit=limit,
        drill_type=drill_type, team_name=team_name,
    )
    return {
        "items": [_serialize(item) for item in items],
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
    }


@router.get("/matrix", response_model=drill_schema.DrillMatrix, summary="F4 消防演练矩阵")
def drill_matrix(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return drill_service.drill_service.matrix(db, viewer=current_user)


@router.post("", response_model=drill_schema.DrillRecord, status_code=201, summary="F2 演练登记")
def create_drill(
    data: drill_schema.DrillCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    _require_admin(current_user)
    return _serialize(drill_service.drill_service.create(db, data=data))


@router.get("/{drill_id}", response_model=drill_schema.DrillDetail, summary="查看演练详情")
def get_drill(
    drill_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = drill_service.drill_service.get_detail(db, viewer=current_user, drill_id=drill_id)
    payload = _serialize(record)
    payload["participants"] = [
        {
            "id": p.id,
            "drill_id": p.drill_id,
            "ehr_id": p.ehr_id,
            "name": p.name,
            "participated": p.participated,
        }
        for p in getattr(record, "_participants", [])
    ]
    return payload


@router.delete("/{drill_id}", status_code=204, summary="删除演练记录")
def delete_drill(
    drill_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    _require_admin(current_user)
    drill_service.drill_service.delete(db, drill_id=drill_id)


_DRILL_COLS = ["活动日期", "演练类型", "地点", "EHR号", "姓名", "是否参与"]


@router.post("/import", response_model=drill_schema.DrillImportSummary, summary="F3 消防演练批量导入")
async def import_drills(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
):
    _require_admin(current_user)
    if file.content_type not in {
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    }:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")
    try:
        import pandas as pd
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"pandas 未安装, 无法解析 Excel: {exc}")

    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        df = pd.read_csv(buffer) if file.content_type == "text/csv" else pd.read_excel(buffer)
        missing = [col for col in _DRILL_COLS if col not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"缺少必填列: {', '.join(missing)}")

        rows = []
        parse_failures = []
        for idx, raw in df.iterrows():
            row_number = int(idx) + 2
            try:
                activity_date = pd.to_datetime(raw["活动日期"]).date()
                participated = raw["是否参与"]
                if isinstance(participated, str):
                    participated = participated.strip().lower() in {"是", "参与", "true", "1", "y"}
                else:
                    participated = bool(participated)
                rows.append(drill_schema.DrillImportRow(
                    row_number=row_number,
                    activity_date=activity_date,
                    drill_type=str(raw["演练类型"]).strip(),
                    location=str(raw["地点"]).strip(),
                    ehr_id=str(raw["EHR号"]).strip(),
                    name=str(raw["姓名"]).strip(),
                    participated=participated,
                ))
            except Exception as exc:
                parse_failures.append({
                    "row_number": row_number,
                    "ehr_id": str(raw.get("EHR号", "")),
                    "reason": f"行解析失败: {type(exc).__name__}: {exc}",
                })

        summary = drill_service.drill_service.import_rows(db, rows=rows)
        summary.failed_rows.extend(parse_failures)
        summary.failed_count = len(summary.failed_rows)
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {type(exc).__name__}: {exc}")
