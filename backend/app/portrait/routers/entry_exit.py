"""
portrait /entry-exit 路由 (PRD §10.1 F5-F9)

端点:
  GET    /entry-exit                 F5 列表 (分页 + 姓名/EHR/团队/年份筛选 + 顶部统计卡)
  POST   /entry-exit                 F6 新增 (17 列, 仅 admin)
  GET    /entry-exit/{id}            F7 查看 (只读)
  PUT    /entry-exit/{id}            F8 编辑 (仅 admin)
  DELETE /entry-exit/{id}            F8 删除 (仅 admin)
  POST   /entry-exit/import          F9 批量导入 (Excel, 仅 admin)
"""
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait.schemas import entry_exit as entry_exit_schema
from app.portrait.services import entry_exit_service

router = APIRouter()


def _serialize(record) -> dict:
    return {
        "id": record.id,
        "ehr_id": record.ehr_id,
        "name": record.name,
        "team_name": record.team_name,
        "position": record.position,
        "certificate_no": record.certificate_no,
        "outbound_reason": record.outbound_reason,
        "destination": record.destination,
        "apply_depart_at": record.apply_depart_at,
        "apply_return_at": record.apply_return_at,
        "certificate_type": record.certificate_type,
        "apply_type": record.apply_type,
        "team_approver": record.team_approver,
        "actual_depart_at": record.actual_depart_at,
        "actual_return_at": record.actual_return_at,
        "year": record.year,
        "group_name": record.group_name,
        "remark": record.remark,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _require_admin(current_user: models.User) -> None:
    """出入境台账写入权限: 仅 admin (PRD §13: 出入境台账写 = admin)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


@router.get(
    "", response_model=entry_exit_schema.EntryExitListResponse, summary="F5 出入境台账列表"
)
def list_entry_exit(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ehr_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    team_name: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    include_statistics: bool = Query(True, alias="stats"),
):
    """F5 列表: admin 全员 / leader 本组 / user 仅自己.
    include_statistics 可选, 默认返回顶部统计卡 (F5 顶部 4 卡).
    """
    items, total = entry_exit_service.list_records(
        db, viewer=current_user, skip=skip, limit=limit,
        ehr_id=ehr_id, name=name, team_name=team_name, year=year,
    )
    stats = entry_exit_service.statistics(db, viewer=current_user) if include_statistics else None
    return entry_exit_schema.EntryExitListResponse(
        items=[_serialize(r) for r in items],
        total=total,
        page=skip // limit + 1,
        size=limit,
        statistics=stats,
    )


@router.post(
    "", response_model=entry_exit_schema.EntryExitRecord,
    status_code=201, summary="F6 新增出入境记录",
)
def create_entry_exit(
    data: entry_exit_schema.EntryExitCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """F6 新增 (17 列, 仅 admin)"""
    _require_admin(current_user)
    record = entry_exit_service.create(db, data=data)
    return _serialize(record)


@router.get(
    "/{record_id}", response_model=entry_exit_schema.EntryExitRecord, summary="F7 查看出入境记录"
)
def get_entry_exit(
    record_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """F7 查看 (只读, admin/leader 本组/本人)"""
    record = entry_exit_service.get_record(db, viewer=current_user, record_id=record_id)
    return _serialize(record)


@router.put(
    "/{record_id}", response_model=entry_exit_schema.EntryExitRecord, summary="F8 编辑出入境记录"
)
def update_entry_exit(
    record_id: int,
    data: entry_exit_schema.EntryExitUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """F8 编辑 (仅 admin)"""
    _require_admin(current_user)
    record = entry_exit_service.get_record(db, viewer=current_user, record_id=record_id)
    record = entry_exit_service.update(db, record=record, data=data)
    return _serialize(record)


@router.delete("/{record_id}", status_code=204, summary="F8 删除出入境记录")
def delete_entry_exit(
    record_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """F8 删除 (仅 admin, PRD §13)"""
    _require_admin(current_user)
    record = entry_exit_service.get_record(db, viewer=current_user, record_id=record_id)
    entry_exit_service.delete(db, record=record)


# 模板列定义, 与 routers/templates.py entry_exit 模板保持一致
_ENTRY_EXIT_COLS = [
    "姓名", "团队", "职务", "证照号", "出境原因", "目的地",
    "申请离境", "申请返回", "证照类别", "申请类型", "团队审批人",
    "实际出境", "实际返回", "年份", "组别", "备注", "EHR号",
]


@router.post(
    "/import", response_model=entry_exit_schema.EntryExitImportSummary,
    summary="F9 出入境批量导入 (Excel)",
)
async def import_entry_exit(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
):
    """F9 批量导入 (17 列 Excel, 仅 admin)"""
    _require_admin(current_user)
    if file.content_type not in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    ]:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")

    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(status_code=500, detail="pandas 未安装, 无法解析 Excel")

    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        if file.content_type == "text/csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)

        for col in _ENTRY_EXIT_COLS:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"缺少必填列: {col}")

        def _parse_dt(value) -> Optional[datetime]:
            if value is None or (isinstance(value, float) and __import__("math").isnan(value)):
                return None
            try:
                return pd.to_datetime(value).to_pydatetime()
            except Exception:
                return None

        valid_rows = []
        parse_failures = []
        for idx, row in df.iterrows():
            row_number = int(idx) + 2
            try:
                raw_year = row["年份"]
                year = int(raw_year)
                if not (2000 <= year <= 2100):
                    raise ValueError(f"年份 {year} 超出范围")
                valid_rows.append(
                    entry_exit_schema.EntryExitImportRow(
                        row_number=row_number,
                        ehr_id=str(row["EHR号"]).strip(),
                        name=str(row["姓名"]).strip(),
                        team_name=str(row["团队"]).strip(),
                        position=str(row["职务"]).strip(),
                        certificate_no=str(row["证照号"]).strip(),
                        outbound_reason=str(row["出境原因"]).strip(),
                        destination=str(row["目的地"]).strip(),
                        apply_depart_at=_parse_dt(row["申请离境"]),
                        apply_return_at=_parse_dt(row["申请返回"]),
                        certificate_type=str(row["证照类别"]).strip(),
                        apply_type=str(row["申请类型"]).strip(),
                        team_approver=str(row["团队审批人"]).strip(),
                        actual_depart_at=_parse_dt(row.get("实际出境")),
                        actual_return_at=_parse_dt(row.get("实际返回")),
                        year=year,
                        group_name=str(row.get("组别")).strip() if not pd.isna(row.get("组别")) else None,
                        remark=str(row.get("备注")).strip() if not pd.isna(row.get("备注")) else None,
                    )
                )
            except Exception as exc:
                parse_failures.append({
                    "row_number": row_number,
                    "ehr_id": str(row.get("EHR号", "")),
                    "reason": f"行解析失败: {type(exc).__name__}: {exc}",
                })

        summary = entry_exit_service.import_rows(db, rows=valid_rows)
        summary.failed_rows.extend(parse_failures)
        summary.failed_count = len(summary.failed_rows)
        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {type(exc).__name__}: {exc}")