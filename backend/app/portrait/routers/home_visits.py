"""
portrait /home-visits 路由 (PRD §C §9.1 P6)

集成指南 §3 阶段 4: portrait P6 家访审批流后端
集成指南 §5 雷区 7: 永远走 Depends

端点:
  POST   /home-visits                       创建家访草稿 (leader)
  GET    /home-visits                       列表 (admin/leader/user 按权限隔离)
  GET    /home-visits/{id}                  详情
  PUT    /home-visits/{id}                  更新草稿 (仅 draft)
  POST   /home-visits/{id}/submit           提交审批 (draft → pending)
  POST   /home-visits/{id}/cancel           撤回 (pending → cancelled, 仅本人)
  POST   /home-visits/{id}/approve          审批通过 (admin/current_approver)
  POST   /home-visits/{id}/reject           审批驳回 (必须 comment)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models  # noqa: F401 触发 ORM 注册
from app.portrait.schemas import (
    HomeVisit,
    HomeVisitApproveRequest,
    HomeVisitCreate,
    HomeVisitListResponse,
    HomeVisitRejectRequest,
    HomeVisitSubmitRequest,
    HomeVisitUpdate,
)
from app.portrait.services import home_visit_service


router = APIRouter()


def _serialize(record: portrait_models.HomeVisitRecord, db: Session) -> dict:
    """HomeVisitRecord ORM -> dict (含 visited_user / visitor_user / current_approver 字段)
    Rule 8: 复用 ORM + 显式字段映射
    """
    visited = (
        db.query(models.User).filter(models.User.id == record.visited_user_id).first()
    )
    visitor = (
        db.query(models.User).filter(models.User.id == record.visitor_user_id).first()
    )
    current_approver = None
    if record.current_approver_id:
        current_approver = (
            db.query(models.User).filter(models.User.id == record.current_approver_id).first()
        )

    return {
        "id": record.id,
        "visited_user_id": record.visited_user_id,
        "visited_ehr_id": visited.ehr_id if visited else None,
        "visited_name": visited.name if visited else None,
        "visitor_user_id": record.visitor_user_id,
        "visitor_name": visitor.name if visitor else None,
        "visit_year": record.visit_year,
        "visit_time": record.visit_time,
        "visit_method": record.visit_method,
        "visit_address": record.visit_address,
        "visitor_info": record.visitor_info,
        "is_visited": record.is_visited,
        "visit_date": record.visit_date,
        "position": record.position,
        "contact_phone": record.contact_phone,
        "address": record.address,
        "mobile": record.mobile,
        "home_phone": record.home_phone,
        "family1_name": record.family1_name,
        "family1_relation": record.family1_relation,
        "family1_contact": record.family1_contact,
        "family1_work_unit": record.family1_work_unit,
        "family2_name": record.family2_name,
        "family2_relation": record.family2_relation,
        "family2_contact": record.family2_contact,
        "family2_work_unit": record.family2_work_unit,
        "feedback": record.feedback,
        "status": record.status,
        "current_approver_id": record.current_approver_id,
        "current_approver_name": current_approver.name if current_approver else None,
        "submitted_at": record.submitted_at,
        "completed_at": record.completed_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@router.post("", response_model=HomeVisit, summary="P6 组长创建家访草稿")
def create_home_visit(
    data: HomeVisitCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """组长创建家访草稿 (status=draft, 需 submit 提交审批)"""
    record = home_visit_service.create_draft(db, visitor=current_user, data=data)
    return _serialize(record, db)


@router.get("", response_model=HomeVisitListResponse, summary="P6 家访列表 (按角色隔离)")
def list_home_visits(
    db: Session = Depends(deps.get_db),
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(draft|pending|approved|rejected|cancelled)$"
    ),
    visit_year: Optional[int] = None,
    visited_ehr_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """列表 (admin 全, leader 本组, user 自己被家访)"""
    items = home_visit_service.list_visits(
        db,
        viewer=current_user,
        status_filter=status_filter,
        visit_year=visit_year,
        visited_ehr_id=visited_ehr_id,
        skip=skip,
        limit=limit,
    )

    list_items = []
    for r in items:
        visited = db.query(models.User).filter(models.User.id == r.visited_user_id).first()
        visitor = db.query(models.User).filter(models.User.id == r.visitor_user_id).first()
        approver = None
        if r.current_approver_id:
            approver = (
                db.query(models.User).filter(models.User.id == r.current_approver_id).first()
            )
        from app.portrait.schemas.home_visit import HomeVisitListItem
        list_items.append(
            HomeVisitListItem(
                id=r.id,
                visited_ehr_id=visited.ehr_id if visited else "",
                visited_name=visited.name if visited else "",
                visit_year=r.visit_year,
                visit_time=r.visit_time,
                visit_method=r.visit_method,
                is_visited=r.is_visited,
                status=r.status,
                submitted_at=r.submitted_at,
                completed_at=r.completed_at,
                visitor_name=visitor.name if visitor else None,
                current_approver_name=approver.name if approver else None,
                created_at=r.created_at,
            )
        )

    return HomeVisitListResponse(total=len(list_items), items=list_items)


@router.get("/{visit_id}", response_model=HomeVisit, summary="P6 家访详情")
def get_home_visit(
    visit_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.get_visit(db, visit_id=visit_id, viewer=current_user)
    return _serialize(record, db)


@router.put("/{visit_id}", response_model=HomeVisit, summary="更新家访草稿 (仅 draft)")
def update_home_visit(
    visit_id: int,
    data: HomeVisitUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.get_visit(db, visit_id=visit_id, viewer=current_user)
    if record.visitor_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅创建人可更新草稿")
    if record.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"状态 {record.status} 不可编辑, 仅 draft 可编辑"
        )

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(record, k, v)
    record.updated_at = datetime.now()
    db.commit()
    db.refresh(record)
    return _serialize(record, db)


@router.post("/{visit_id}/submit", response_model=HomeVisit, summary="P6 提交审批 (draft → pending)")
def submit_home_visit(
    visit_id: int,
    data: HomeVisitSubmitRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.submit(
        db, visit_id=visit_id, viewer=current_user, next_approver_id=data.next_approver_id
    )
    return _serialize(record, db)


@router.post("/{visit_id}/cancel", response_model=HomeVisit, summary="P6 撤回 (pending → cancelled)")
def cancel_home_visit(
    visit_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.cancel(db, visit_id=visit_id, viewer=current_user)
    return _serialize(record, db)


@router.post("/{visit_id}/approve", response_model=HomeVisit, summary="P6 审批通过 (admin/current_approver)")
def approve_home_visit(
    visit_id: int,
    data: HomeVisitApproveRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.approve(
        db, visit_id=visit_id, viewer=current_user, comment=data.comment
    )
    return _serialize(record, db)


@router.post("/{visit_id}/reject", response_model=HomeVisit, summary="P6 审批驳回 (必须 comment)")
def reject_home_visit(
    visit_id: int,
    data: HomeVisitRejectRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.reject(
        db, visit_id=visit_id, viewer=current_user, comment=data.comment
    )
    return _serialize(record, db)