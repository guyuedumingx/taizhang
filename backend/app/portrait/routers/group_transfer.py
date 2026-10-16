"""
portrait /group-transfers 路由 (PRD §11.4 G7 组员调换历史)

端点:
  GET    /group-transfers             列表 (分页 + EHR/姓名/年份/是否当前在组筛选)
  DELETE /group-transfers/{record_id} 删除 (仅 admin, 纠错用)

**没有 POST / PUT** —— 记录由 team_id 变更自动写入, 手工新增会造假
(用户 2026-10-12 决定)。调 POST 会返回 405, 这是预期行为。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models
from app.portrait.schemas import group_transfer as group_transfer_schema
from app.portrait.services import group_transfer_service

router = APIRouter()


def _serialize(record) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "user_name": record.user.name if record.user else None,
        "ehr_no": record.ehr_no,
        "from_group": record.from_group,
        "to_group": record.to_group,
        "from_team_id": record.from_team_id,
        "to_team_id": record.to_team_id,
        "transfer_date": record.transfer_date,
        "leave_date": record.leave_date,
        "is_current": record.leave_date is None,
        "operator_ehr_no": record.operator_ehr_no,
        "operator_name": record.operator_name,
        "reason": record.reason,
        "remark": record.remark,
        "created_at": record.created_at,
    }


def _require_admin(current_user: models.User) -> None:
    """删除仅 admin: 历史记录不可篡改, 只有纠错这一种删除场景"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


@router.get(
    "",
    response_model=group_transfer_schema.GroupTransferListResponse,
    summary="G7 组员调换历史列表",
)
def list_group_transfers(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ehr_id: Optional[str] = Query(None, description="员工 EHR 号 (精确)"),
    name: Optional[str] = Query(None, description="姓名 (模糊)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="调组年份"),
    is_current: Optional[bool] = Query(
        None, description="true=只看当前在组, false=只看已离开"
    ),
):
    """admin 全员 / 组长本组相关 (按 team_id 比对, 不按组名)。"""
    items, total = group_transfer_service.list_records(
        db,
        viewer=current_user,
        skip=skip,
        limit=limit,
        ehr_id=ehr_id,
        name=name,
        year=year,
        is_current=is_current,
    )
    return group_transfer_schema.GroupTransferListResponse(
        items=[_serialize(r) for r in items],
        total=total,
        page=skip // limit + 1,
        size=limit,
    )


@router.delete("/{record_id}", status_code=204, summary="G7 删除调换记录 (仅 admin 纠错)")
def delete_group_transfer(
    record_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """删除一条**已关闭**的记录。「当前在组」的那条禁止删 —— 它是可见性的锚点。"""
    _require_admin(current_user)
    record = db.query(portrait_models.GroupTransferHistory).filter(
        portrait_models.GroupTransferHistory.id == record_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"调组记录 {record_id} 不存在")
    group_transfer_service.delete(db, record=record)