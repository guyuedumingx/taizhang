"""
portrait Submission 状态机 service (核心)

集成指南 §3 阶段 4 + PRD §9.1:
  3 类提交 + 审批工作台, 自建状态机 (不依赖台账 WorkflowInstance, 因其 ledger_id NOT NULL+UNIQUE)

状态机:
  draft ──submit──> pending ──approve──> approved
                         │
                         ├──reject──> rejected
                         │
                         └──withdraw──> cancelled

业务效果 (approval 通过时触发):
  - special_work   : 暂不写业务表 (P5+ 才接 ProjectSummary)
  - profile_edit   : 暂不应用 field 改动 (P5+ 接入)
  - skill_tag_edit : 暂不写 skill_tags (P5+ 接入)

集成指南 §5 雷区 12 (Rule 12): 错误显性化, 失败抛 HTTPException 不吞掉
"""
import json
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.portrait import models as portrait_models
from app.portrait.schemas import submission as sub_schema
from app.utils.logger import log_info


VALID_TYPES = {"special_work", "profile_edit", "skill_tag_edit"}
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"
DRAFT = "draft"
TERMINAL_STATUSES = {APPROVED, REJECTED, CANCELLED}


def _validate_payload(submission_type: str, payload: dict) -> None:
    """payload 字段校验 (按 submission_type 分发, 失败抛 400)"""
    if submission_type == "special_work":
        required = ["project_name", "start_time", "content", "hours"]
        for f in required:
            if f not in payload or payload[f] in (None, ""):
                raise HTTPException(status_code=400, detail=f"special_work 缺少字段: {f}")
    elif submission_type == "profile_edit":
        required = ["field_name", "old_value", "new_value"]
        for f in required:
            if f not in payload or payload[f] in (None, ""):
                raise HTTPException(status_code=400, detail=f"profile_edit 缺少字段: {f}")
    elif submission_type == "skill_tag_edit":
        required = ["tag_name", "action", "sensitivity"]
        for f in required:
            if f not in payload or payload[f] in (None, ""):
                raise HTTPException(status_code=400, detail=f"skill_tag_edit 缺少字段: {f}")
        if payload["action"] not in ("add", "delete"):
            raise HTTPException(status_code=400, detail="skill_tag_edit.action 必须是 add/delete")


def _resolve_next_approver(
    db: Session, *, submission_type: str, submitter: models.User, specified_id: Optional[int]
) -> Optional[int]:
    """计算下一审批人
    - special_work  : submitter 指定 (next_approver_id 必填)
    - profile_edit  : admin role 第一个用户
    - skill_tag_edit: admin role 第一个用户
    """
    if submission_type == "special_work":
        if not specified_id:
            raise HTTPException(
                status_code=400, detail="special_work 必须指定 next_approver_id (审批人下拉)"
            )
        approver = db.query(models.User).filter(models.User.id == specified_id).first()
        if not approver:
            raise HTTPException(status_code=400, detail=f"审批人 {specified_id} 不存在")
        if not approver.is_active:
            raise HTTPException(status_code=400, detail=f"审批人 {approver.ehr_id} 已停用")
        return specified_id

    # profile_edit / skill_tag_edit: 默认 admin 角色
    # taizhang 用 Casbin 管角色绑定, 不在 user.role 字段. 用 is_superuser 找第一个 admin
    admin_user = (
        db.query(models.User)
        .filter(
            models.User.is_superuser == True,  # noqa: E712
            models.User.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not admin_user:
        raise HTTPException(
            status_code=500,
            detail="找不到 is_superuser=True 的 admin 用户处理审批, 请先 init_db",
        )
    if specified_id:
        # 即便有指定, 也允许 (admin 可以转交)
        return specified_id
    return admin_user.id


def _to_dict(model) -> dict:
    """model -> dict (含 from_attributes)"""
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}


class SubmissionService:
    """4 类审批状态机 (3 类 submission + 1 类 home_visit 走 home_visit_service)"""

    # ========================================================================
    # 创建提交 (一步到 pending, MVP 不支持先 draft 后 submit)
    # ========================================================================
    @staticmethod
    def create_submission(
        db: Session,
        *,
        submitter: models.User,
        data: sub_schema.SubmissionCreate,
    ) -> portrait_models.SubmissionRecord:
        """创建并提交 (status=pending)"""
        if data.submission_type not in VALID_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"submission_type 必须是 {VALID_TYPES} 之一, 收到 {data.submission_type}",
            )

        _validate_payload(data.submission_type, data.payload)

        next_approver_id = _resolve_next_approver(
            db,
            submission_type=data.submission_type,
            submitter=submitter,
            specified_id=data.next_approver_id,
        )

        # 找 submitter 对应 portrait_user_metadata 取 ehr (不强制要求有)
        ehr_id = submitter.ehr_id or "0000000"

        submission = portrait_models.SubmissionRecord(
            submission_type=data.submission_type,
            submitter_user_id=submitter.id,
            submitter_name=submitter.name or submitter.username,
            submitter_ehr_id=ehr_id,
            workflow_instance_id=None,  # MVP 阶段不绑台账 workflow_instance
            current_approver_id=next_approver_id,
            status=PENDING,
            payload=json.dumps(data.payload, ensure_ascii=False),
            submitted_at=__import__("datetime").datetime.now(),
        )
        db.add(submission)
        db.flush()

        # 第一条 approval_record: action=submit (留痕)
        submit_record = portrait_models.ApprovalRecord(
            submission_id=submission.id,
            approver_id=submitter.id,
            action="submit",
            comment=None,
            transferred_to_id=None,
        )
        db.add(submit_record)
        db.commit()
        db.refresh(submission)

        log_info(
            module="portrait",
            action="submission.create",
            message=f"提交 {data.submission_type} #{submission.id}",
            user_id=submitter.id,
            resource_type="submission",
            resource_id=str(submission.id),
        )
        return submission

    # ========================================================================
    # 我的提交列表
    # ========================================================================
    @staticmethod
    def list_my_submissions(
        db: Session,
        *,
        submitter: models.User,
        status: Optional[str] = None,
        submission_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[portrait_models.SubmissionRecord]:
        query = db.query(portrait_models.SubmissionRecord).filter(
            portrait_models.SubmissionRecord.submitter_user_id == submitter.id
        )
        if status:
            query = query.filter(portrait_models.SubmissionRecord.status == status)
        if submission_type:
            query = query.filter(
                portrait_models.SubmissionRecord.submission_type == submission_type
            )
        return (
            query.order_by(portrait_models.SubmissionRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_my_submissions(
        db: Session,
        *,
        submitter: models.User,
        status: Optional[str] = None,
        submission_type: Optional[str] = None,
    ) -> int:
        query = db.query(portrait_models.SubmissionRecord).filter(
            portrait_models.SubmissionRecord.submitter_user_id == submitter.id
        )
        if status:
            query = query.filter(portrait_models.SubmissionRecord.status == status)
        if submission_type:
            query = query.filter(
                portrait_models.SubmissionRecord.submission_type == submission_type
            )
        return query.count()

    # ========================================================================
    # 详情 (含审批流)
    # ========================================================================
    @staticmethod
    def get_submission_detail(
        db: Session, *, submission_id: int, viewer: models.User
    ) -> tuple[portrait_models.SubmissionRecord, List[portrait_models.ApprovalRecord]]:
        submission = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id == submission_id)
            .first()
        )
        if not submission:
            raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")

        # 权限: submitter 自己 / 审批人 / admin 都能看
        is_approver = (
            submission.current_approver_id == viewer.id
            or submission.submitter_user_id == viewer.id
        )
        if not (is_approver or viewer.is_superuser):
            raise HTTPException(status_code=403, detail="无权查看该提交")

        approvals = (
            db.query(portrait_models.ApprovalRecord)
            .filter(portrait_models.ApprovalRecord.submission_id == submission_id)
            .order_by(portrait_models.ApprovalRecord.created_at)
            .all()
        )
        return submission, approvals

    # ========================================================================
    # 撤回 (withdraw) - 仅 submitter 本人, 仅 pending 状态
    # ========================================================================
    @staticmethod
    def cancel_submission(
        db: Session, *, submission_id: int, viewer: models.User
    ) -> portrait_models.SubmissionRecord:
        submission = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id == submission_id)
            .first()
        )
        if not submission:
            raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")
        if submission.submitter_user_id != viewer.id:
            raise HTTPException(status_code=403, detail="仅提交人本人可撤回")
        if submission.status != PENDING:
            raise HTTPException(
                status_code=400, detail=f"当前状态 {submission.status} 不可撤回, 仅 pending 可撤回"
            )

        submission.status = CANCELLED
        submission.completed_at = __import__("datetime").datetime.now()

        cancel_record = portrait_models.ApprovalRecord(
            submission_id=submission.id,
            approver_id=viewer.id,
            action="withdraw",
            comment=None,
        )
        db.add(cancel_record)
        db.commit()
        db.refresh(submission)
        return submission

    # ========================================================================
    # 审批: 通过 / 驳回 / 转交 (E2 审批工作台)
    # ========================================================================
    @staticmethod
    def _ensure_can_act(
        submission: portrait_models.SubmissionRecord, viewer: models.User
    ) -> None:
        if submission.status != PENDING:
            raise HTTPException(
                status_code=400, detail=f"提交状态 {submission.status}, 已终结, 不可审批"
            )
        if viewer.is_superuser:
            return
        if submission.current_approver_id != viewer.id:
            raise HTTPException(
                status_code=403, detail="当前用户不是审批人 (仅 current_approver 或 admin 可审批)"
            )

    @staticmethod
    def approve(
        db: Session,
        *,
        submission_id: int,
        viewer: models.User,
        comment: Optional[str] = None,
    ) -> portrait_models.SubmissionRecord:
        submission = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id == submission_id)
            .first()
        )
        if not submission:
            raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")
        SubmissionService._ensure_can_act(submission, viewer)

        submission.status = APPROVED
        submission.completed_at = __import__("datetime").datetime.now()
        submission.current_approver_id = None

        record = portrait_models.ApprovalRecord(
            submission_id=submission.id,
            approver_id=viewer.id,
            action="approve",
            comment=comment,
        )
        db.add(record)
        db.commit()
        db.refresh(submission)

        log_info(
            module="portrait",
            action="submission.approve",
            message=f"通过提交 #{submission.id}",
            user_id=viewer.id,
            resource_type="submission",
            resource_id=str(submission.id),
        )

        # P8 联动: special_work 审批通过 → 自动在台账系统创建对应 ledger
        # 雷区 4 合规: submission commit 之后才联动, 失败抛 500 显性化 (Rule 12)
        if submission.submission_type == "special_work":
            try:
                from app.portrait.services.integration_service import sync_special_work_to_ledger
                new_ledger = sync_special_work_to_ledger(db, submission=submission)
                if new_ledger is not None:
                    db.commit()
                    db.refresh(submission)
            except HTTPException:
                raise  # 已显性化, 继续抛出
            except Exception as exc:
                # 未预期的联动失败 (Rule 12 显性化): 抛 500 不静默
                raise HTTPException(
                    status_code=500,
                    detail=f"special_work 联动台账失败: {exc}",
                ) from exc

        return submission

    @staticmethod
    def reject(
        db: Session,
        *,
        submission_id: int,
        viewer: models.User,
        comment: str,
    ) -> portrait_models.SubmissionRecord:
        if not comment or not comment.strip():
            raise HTTPException(status_code=400, detail="驳回必须填写意见 (Rule 12 显性化)")

        submission = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id == submission_id)
            .first()
        )
        if not submission:
            raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")
        SubmissionService._ensure_can_act(submission, viewer)

        submission.status = REJECTED
        submission.completed_at = __import__("datetime").datetime.now()
        submission.current_approver_id = None

        record = portrait_models.ApprovalRecord(
            submission_id=submission.id,
            approver_id=viewer.id,
            action="reject",
            comment=comment,
        )
        db.add(record)
        db.commit()
        db.refresh(submission)

        log_info(
            module="portrait",
            action="submission.reject",
            message=f"驳回提交 #{submission.id}",
            user_id=viewer.id,
            resource_type="submission",
            resource_id=str(submission.id),
        )
        return submission

    @staticmethod
    def transfer(
        db: Session,
        *,
        submission_id: int,
        viewer: models.User,
        transferred_to_id: int,
        comment: Optional[str] = None,
    ) -> portrait_models.SubmissionRecord:
        if not transferred_to_id:
            raise HTTPException(status_code=400, detail="转交必须指定 transferred_to_id")

        target = db.query(models.User).filter(models.User.id == transferred_to_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"转交目标用户 {transferred_to_id} 不存在")
        if not target.is_active:
            raise HTTPException(status_code=400, detail="转交目标用户已停用")

        submission = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id == submission_id)
            .first()
        )
        if not submission:
            raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")
        SubmissionService._ensure_can_act(submission, viewer)

        submission.current_approver_id = transferred_to_id

        record = portrait_models.ApprovalRecord(
            submission_id=submission.id,
            approver_id=viewer.id,
            action="transfer",
            comment=comment,
            transferred_to_id=transferred_to_id,
        )
        db.add(record)
        db.commit()
        db.refresh(submission)

        log_info(
            module="portrait",
            action="submission.transfer",
            message=f"转交提交 #{submission.id} 给用户 {transferred_to_id}",
            user_id=viewer.id,
            resource_type="submission",
            resource_id=str(submission.id),
        )
        return submission

    # ========================================================================
    # 待审批列表 (E1)
    # ========================================================================
    @staticmethod
    def list_pending_for_user(
        db: Session, *, viewer: models.User, skip: int = 0, limit: int = 50
    ) -> List[portrait_models.SubmissionRecord]:
        """我的待审批 (current_approver_id == viewer.id)"""
        query = db.query(portrait_models.SubmissionRecord).filter(
            portrait_models.SubmissionRecord.status == PENDING,
            portrait_models.SubmissionRecord.current_approver_id == viewer.id,
        )
        return (
            query.order_by(portrait_models.SubmissionRecord.submitted_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_pending_for_user(db: Session, *, viewer: models.User) -> int:
        return (
            db.query(portrait_models.SubmissionRecord)
            .filter(
                portrait_models.SubmissionRecord.status == PENDING,
                portrait_models.SubmissionRecord.current_approver_id == viewer.id,
            )
            .count()
        )

    # ========================================================================
    # 历史审批 (E3 - 我审批过的)
    # ========================================================================
    @staticmethod
    def list_history_for_user(
        db: Session, *, viewer: models.User, skip: int = 0, limit: int = 50
    ) -> List[portrait_models.SubmissionRecord]:
        """我审批过的 submission (作为审批人留痕, 去重 + 按时间倒序)

        实现: 通过 ApprovalRecord.approver_id == viewer.id 查到所有 submission_id,
              去重后查 SubmissionRecord, 按 completed_at 倒序 (审批结束时间最新在前).
        """
        # 1) 拿到我去操作过的所有 submission_id (去重)
        from sqlalchemy import select
        history_sub_ids = select(
            portrait_models.ApprovalRecord.submission_id
        ).where(
            portrait_models.ApprovalRecord.approver_id == viewer.id
        ).distinct()
        # 2) 查 SubmissionRecord, 按 completed_at desc (NullSafe: pending 也会有, 排后)
        query = (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id.in_(history_sub_ids))
        )
        # 用 COALESCE 把 null completed_at 视为很早的时间, 让 null 排到后面
        from sqlalchemy import func, case
        null_safe_completed = case(
            (portrait_models.SubmissionRecord.completed_at.is_(None), "1970-01-01"),
            else_=portrait_models.SubmissionRecord.completed_at,
        )
        return (
            query.order_by(null_safe_completed.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_history_for_user(db: Session, *, viewer: models.User) -> int:
        from sqlalchemy import select
        history_sub_ids = select(
            portrait_models.ApprovalRecord.submission_id
        ).where(
            portrait_models.ApprovalRecord.approver_id == viewer.id
        ).distinct()
        return (
            db.query(portrait_models.SubmissionRecord)
            .filter(portrait_models.SubmissionRecord.id.in_(history_sub_ids))
            .count()
        )


submission_service = SubmissionService()