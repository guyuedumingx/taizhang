"""
portrait /approvals 路由 (PRD E1, E2, E3 审批工作台)

集成指南 §3 阶段 4: portrait P4 后端 API MVP
集成指南 §5 雷区 7: 永远走 Depends
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models
from app.portrait.schemas import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    PaginatedResponse,
    Submission,
)
from app.portrait.services import submission_service


router = APIRouter()


def _serialize_submission(sub: portrait_models.SubmissionRecord) -> dict:
    return {
        "id": sub.id,
        "submission_type": sub.submission_type,
        "submitter_user_id": sub.submitter_user_id,
        "submitter_name": sub.submitter_name,
        "submitter_ehr_id": sub.submitter_ehr_id,
        "workflow_instance_id": sub.workflow_instance_id,
        "current_approver_id": sub.current_approver_id,
        "status": sub.status,
        "payload": sub.payload,
        "submitted_at": sub.submitted_at,
        "completed_at": sub.completed_at,
        "created_at": sub.created_at,
        "updated_at": sub.updated_at,
        "synced_ledger_id": getattr(sub, "synced_ledger_id", None),  # P8 联动字段
    }


@router.get("/pending", response_model=PaginatedResponse[Submission], summary="E1 我的待审批")
def list_pending(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> PaginatedResponse[Submission]:
    """我的待审批 (current_approver_id == user.id, 4 类合并)"""
    items = submission_service.list_pending_for_user(
        db, viewer=current_user, skip=skip, limit=limit
    )
    total = submission_service.count_pending_for_user(db, viewer=current_user)
    serialized = [_serialize_submission(s) for s in items]
    return PaginatedResponse[Submission](
        items=serialized, total=total, page=skip // limit + 1, size=limit
    )


@router.get("/history", response_model=PaginatedResponse[Submission], summary="E3 我审批过的历史")
def list_history(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> PaginatedResponse[Submission]:
    """我审批过的 submission (作为审批人留痕, 去重 + 按 completed_at desc)"""
    items = submission_service.list_history_for_user(
        db, viewer=current_user, skip=skip, limit=limit
    )
    total = submission_service.count_history_for_user(db, viewer=current_user)
    serialized = [_serialize_submission(s) for s in items]
    return PaginatedResponse[Submission](
        items=serialized, total=total, page=skip // limit + 1, size=limit
    )


@router.post(
    "/{submission_id}/approve",
    response_model=ApprovalActionResponse,
    summary="E2 审批通过",
)
def approve(
    submission_id: int,
    body: ApprovalActionRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ApprovalActionResponse:
    sub = submission_service.approve(
        db, submission_id=submission_id, viewer=current_user, comment=body.comment
    )
    # P8: integration_service 可能在 service.approve 后写回 synced_ledger_id,
    # 序列化前 refresh 确保拿到最新值
    db.refresh(sub)
    return ApprovalActionResponse(
        success=True, message="已通过", submission=_serialize_submission(sub)
    )


@router.post(
    "/{submission_id}/reject",
    response_model=ApprovalActionResponse,
    summary="E2 审批驳回",
)
def reject(
    submission_id: int,
    body: ApprovalActionRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ApprovalActionResponse:
    if not body.comment or not body.comment.strip():
        raise HTTPException(status_code=400, detail="驳回必须填写意见")
    sub = submission_service.reject(
        db, submission_id=submission_id, viewer=current_user, comment=body.comment
    )
    return ApprovalActionResponse(
        success=True, message="已驳回", submission=_serialize_submission(sub)
    )


@router.post(
    "/{submission_id}/transfer",
    response_model=ApprovalActionResponse,
    summary="E2 审批转交",
)
def transfer(
    submission_id: int,
    body: ApprovalActionRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ApprovalActionResponse:
    if not body.transferred_to_id:
        raise HTTPException(status_code=400, detail="转交必须指定 transferred_to_id")
    sub = submission_service.transfer(
        db,
        submission_id=submission_id,
        viewer=current_user,
        transferred_to_id=body.transferred_to_id,
        comment=body.comment,
    )
    return ApprovalActionResponse(
        success=True, message=f"已转交给用户 {body.transferred_to_id}", submission=_serialize_submission(sub)
    )