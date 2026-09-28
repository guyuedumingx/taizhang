"""
portrait /submissions 路由 (PRD B1, B3, B4)

集成指南 §3 阶段 4: portrait P4 后端 API MVP
集成指南 §5 雷区 7: 永远走 Depends
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models
from app.portrait.schemas import (
    PaginatedResponse,
    Submission,
    SubmissionCreate,
    SubmissionDetail,
)
from app.portrait.services import submission_service


router = APIRouter()


def _serialize_submission(sub: portrait_models.SubmissionRecord) -> dict:
    """Submission ORM -> dict (含 payload 反序列化 + 关联字段)
    Rule 8: 避免再起一套 dict, 复用 ORM
    """
    base = {
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
    return base


@router.post("", response_model=Submission, status_code=status.HTTP_201_CREATED, summary="B1 创建提交")
def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """创建并提交 (3 类: special_work / profile_edit / skill_tag_edit)"""
    sub = submission_service.create_submission(db, submitter=current_user, data=data)
    return _serialize_submission(sub)


@router.get("/me", response_model=PaginatedResponse[Submission], summary="B3 我的提交列表")
def list_my_submissions(
    db: Session = Depends(deps.get_db),
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(draft|pending|approved|rejected|cancelled)$"
    ),
    submission_type: Optional[str] = Query(
        None, pattern="^(special_work|profile_edit|skill_tag_edit)$"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> PaginatedResponse[Submission]:
    """我的提交列表 (status / submission_type 可选筛选)"""
    items = submission_service.list_my_submissions(
        db,
        submitter=current_user,
        status=status_filter,
        submission_type=submission_type,
        skip=skip,
        limit=limit,
    )
    total = submission_service.count_my_submissions(
        db,
        submitter=current_user,
        status=status_filter,
        submission_type=submission_type,
    )
    serialized = [_serialize_submission(s) for s in items]
    return PaginatedResponse[Submission](
        items=serialized, total=total, page=skip // limit + 1, size=limit
    )


@router.get("/{submission_id}", response_model=SubmissionDetail, summary="B4 提交详情")
def get_submission_detail(
    submission_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> SubmissionDetail:
    """提交详情 (含审批流 ApprovalRecord 列表)"""
    sub, approvals = submission_service.get_submission_detail(
        db, submission_id=submission_id, viewer=current_user
    )
    base = _serialize_submission(sub)
    approvals_dicts = [
        {
            "id": a.id,
            "submission_id": a.submission_id,
            "approver_id": a.approver_id,
            "action": a.action,
            "comment": a.comment,
            "transferred_to_id": a.transferred_to_id,
            "created_at": a.created_at,
        }
        for a in approvals
    ]
    return {**base, "approvals": approvals_dicts}


@router.delete("/{submission_id}", response_model=Submission, summary="撤回提交")
def cancel_submission(
    submission_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Submission:
    """撤回 (仅 submitter 本人, 仅 pending 状态)"""
    sub = submission_service.cancel_submission(
        db, submission_id=submission_id, viewer=current_user
    )
    return _serialize_submission(sub)