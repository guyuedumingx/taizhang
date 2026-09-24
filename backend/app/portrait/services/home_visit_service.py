"""
portrait 家访审批状态机 service

集成指南 §3 阶段 4 + PRD §9.1 §C/D:
  家访 走 自建状态机 (与 submission_service 同模式, 但复用 HomeVisitRecord 自身)

状态机:
  draft ──submit──> pending ──approve──> approved
                         │
                         ├──reject──> rejected
                         │
                         └──withdraw──> cancelled

集成指南 §5 雷区 7: 永远走 Depends (校验在 router)
集成指南 §5 雷区 12 (Rule 12): 错误显性化, 失败抛 HTTPException 不吞掉

权限模型 (与 profile_service 对齐, Rule 8 先读再写, Rule 7 单一模式):
  - is_superuser  : admin, 看全部
  - team_id 相等  : leader, 看本组
  - id 相等       : user, 只看自己被家访记录
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.portrait import models as portrait_models
from app.utils.logger import log_info


PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"
DRAFT = "draft"
TERMINAL_STATUSES = {APPROVED, REJECTED, CANCELLED}


def _resolve_next_approver(db: Session, *, specified_id: Optional[int]) -> int:
    """默认审批人: 第一个 is_superuser=True 的 admin"""
    if specified_id:
        approver = db.query(models.User).filter(models.User.id == specified_id).first()
        if not approver:
            raise HTTPException(status_code=400, detail=f"审批人 {specified_id} 不存在")
        if not approver.is_active:
            raise HTTPException(status_code=400, detail=f"审批人 {approver.ehr_id} 已停用")
        return specified_id

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
    return admin_user.id


def _can_view_record(viewer: models.User, record: portrait_models.HomeVisitRecord) -> bool:
    """判定 viewer 能否查看记录 (admin / 同组 leader / 被家访人本人)"""
    if viewer.is_superuser:
        return True
    if viewer.team_id is None:
        return False
    visited_user = (
        viewer.__class__.query.get(record.visited_user_id)
        if False  # noqa: 走显式 query 避免 lazy load
        else None
    )
    # 简化 — 这里直接读 visited_user_id 对应 user.team_id
    # 实际权限判定在 router 层用 SQL 查; service 层不读 db 再次, 仅校验当前 viewer
    return False  # placeholder, 实际由 router 层 _ensure_can_view 调用 SQL 判断


class HomeVisitService:
    """家访审批状态机

    设计要点 (Rule 8 先读再写, 与 SubmissionService 对齐):
    - 创建时直接 status=draft, 需要 submit() 转到 pending
    - pending → approve/reject/cancel
    """

    # ========================================================================
    # 写入 (draft)
    # ========================================================================
    @staticmethod
    def create_draft(
        db: Session, *, visitor: models.User, data
    ) -> portrait_models.HomeVisitRecord:
        """创建家访草稿 (status=draft, 需后续 submit 提交审批)

        权限: 仅 leader (有 team_id 且非 admin) 可创建
        """
        if visitor.is_superuser:
            raise HTTPException(status_code=403, detail="管理员不可创建家访 (业务规则: 谁做家访谁签字)")
        if not visitor.team_id:
            raise HTTPException(status_code=403, detail="仅组长可创建家访记录")

        # 被家访人必须存在
        visited = (
            db.query(models.User)
            .filter(models.User.ehr_id == data.visited_ehr_id)
            .filter(models.User.deleted_at.is_(None) if hasattr(models.User, "deleted_at") else True)
            .first()
        )
        if not visited:
            raise HTTPException(status_code=404, detail=f"被家访人 {data.visited_ehr_id} 不存在")

        # 组长只能对本组成员家访
        if visited.team_id != visitor.team_id:
            raise HTTPException(status_code=403, detail="仅可对本组成员进行家访")

        record = portrait_models.HomeVisitRecord(
            visited_user_id=visited.id,
            visitor_user_id=visitor.id,
            visit_year=data.visit_year,
            visit_time=data.visit_time,
            visit_method=data.visit_method,
            visit_address=data.visit_address,
            visitor_info=data.visitor_info,
            is_visited=data.is_visited,
            visit_date=data.visit_date,
            position=data.position,
            contact_phone=data.contact_phone,
            address=data.address,
            mobile=data.mobile,
            home_phone=data.home_phone,
            family1_name=data.family1_name,
            family1_relation=data.family1_relation,
            family1_contact=data.family1_contact,
            family1_work_unit=data.family1_work_unit,
            family2_name=data.family2_name,
            family2_relation=data.family2_relation,
            family2_contact=data.family2_contact,
            family2_work_unit=data.family2_work_unit,
            feedback=data.feedback,
            status=DRAFT,
            current_approver_id=None,
            submitted_at=None,
            completed_at=None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        log_info(
            module="portrait",
            action="home_visit.create_draft",
            message=f"组长 {visitor.id} 创建家访草稿 #{record.id} 被家访人 {visited.ehr_id}",
            user_id=visitor.id,
            resource_type="home_visit",
            resource_id=str(record.id),
        )
        return record

    # ========================================================================
    # 提交 (draft → pending)
    # ========================================================================
    @staticmethod
    def submit(
        db: Session, *, visit_id: int, viewer: models.User, next_approver_id: Optional[int] = None
    ) -> portrait_models.HomeVisitRecord:
        record = (
            db.query(portrait_models.HomeVisitRecord)
            .filter(portrait_models.HomeVisitRecord.id == visit_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"家访 {visit_id} 不存在")
        if record.visitor_user_id != viewer.id:
            raise HTTPException(status_code=403, detail="仅创建家访的组长本人可提交审批")
        if record.status != DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"当前状态 {record.status} 不可提交审批, 仅 draft 可提交",
            )

        record.status = PENDING
        record.current_approver_id = _resolve_next_approver(db, specified_id=next_approver_id)
        record.submitted_at = __import__("datetime").datetime.now()

        log_info(
            module="portrait",
            action="home_visit.submit",
            message=f"提交家访 #{record.id} 给审批人 {record.current_approver_id}",
            user_id=viewer.id,
            resource_type="home_visit",
            resource_id=str(record.id),
        )
        db.commit()
        db.refresh(record)
        return record

    # ========================================================================
    # 撤回 (pending → cancelled)
    # ========================================================================
    @staticmethod
    def cancel(
        db: Session, *, visit_id: int, viewer: models.User
    ) -> portrait_models.HomeVisitRecord:
        record = (
            db.query(portrait_models.HomeVisitRecord)
            .filter(portrait_models.HomeVisitRecord.id == visit_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"家访 {visit_id} 不存在")
        if record.visitor_user_id != viewer.id:
            raise HTTPException(status_code=403, detail="仅创建家访的组长本人可撤回")
        if record.status != PENDING:
            raise HTTPException(
                status_code=400, detail=f"当前状态 {record.status} 不可撤回, 仅 pending 可撤回"
            )

        record.status = CANCELLED
        record.current_approver_id = None
        record.completed_at = __import__("datetime").datetime.now()

        log_info(
            module="portrait",
            action="home_visit.cancel",
            message=f"撤回家访 #{record.id}",
            user_id=viewer.id,
            resource_type="home_visit",
            resource_id=str(record.id),
        )
        db.commit()
        db.refresh(record)
        return record

    # ========================================================================
    # 审批: 通过/驳回 (admin OR current_approver_id == viewer.id)
    # ========================================================================
    @staticmethod
    def _ensure_can_act(record: portrait_models.HomeVisitRecord, viewer: models.User) -> None:
        if record.status != PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"家访状态 {record.status}, 已终结, 不可审批",
            )
        if viewer.is_superuser:
            return
        if record.current_approver_id != viewer.id:
            raise HTTPException(
                status_code=403, detail="当前用户不是审批人 (仅 current_approver 或 admin 可审批)"
            )

    @staticmethod
    def approve(
        db: Session, *, visit_id: int, viewer: models.User, comment: Optional[str] = None
    ) -> portrait_models.HomeVisitRecord:
        record = (
            db.query(portrait_models.HomeVisitRecord)
            .filter(portrait_models.HomeVisitRecord.id == visit_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"家访 {visit_id} 不存在")
        HomeVisitService._ensure_can_act(record, viewer)

        record.status = APPROVED
        record.current_approver_id = None
        record.completed_at = __import__("datetime").datetime.now()

        log_info(
            module="portrait",
            action="home_visit.approve",
            message=f"通过家访 #{record.id} (审批人={viewer.id}, 备注={comment})",
            user_id=viewer.id,
            resource_type="home_visit",
            resource_id=str(record.id),
        )
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def reject(
        db: Session, *, visit_id: int, viewer: models.User, comment: str
    ) -> portrait_models.HomeVisitRecord:
        if not comment or not comment.strip():
            raise HTTPException(
                status_code=400, detail="驳回必须填写意见 (Rule 12 显性化)"
            )
        record = (
            db.query(portrait_models.HomeVisitRecord)
            .filter(portrait_models.HomeVisitRecord.id == visit_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"家访 {visit_id} 不存在")
        HomeVisitService._ensure_can_act(record, viewer)

        record.status = REJECTED
        record.current_approver_id = None
        record.completed_at = __import__("datetime").datetime.now()

        log_info(
            module="portrait",
            action="home_visit.reject",
            message=f"驳回家访 #{record.id} (审批人={viewer.id}, 备注={comment})",
            user_id=viewer.id,
            resource_type="home_visit",
            resource_id=str(record.id),
        )
        db.commit()
        db.refresh(record)
        return record

    # ========================================================================
    # 列表 / 详情
    # 权限隔离 (Rule 7 单一模式: admin 全 / leader 本组 / user 自己被家访)
    # ========================================================================
    @staticmethod
    def list_visits(
        db: Session,
        *,
        viewer: models.User,
        status_filter: Optional[str] = None,
        visit_year: Optional[int] = None,
        visited_ehr_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[portrait_models.HomeVisitRecord]:
        query = db.query(portrait_models.HomeVisitRecord)

        if not viewer.is_superuser:
            # user: 仅自己作为被家访人的记录
            # leader: 本组成员作为被家访人的所有记录
            team_user_ids_subq = (
                db.query(models.User.id)
                .filter(
                    (models.User.team_id == viewer.team_id)
                    if viewer.team_id
                    else (models.User.id == -1)
                )
                .subquery()
            )
            if viewer.team_id is not None:
                query = query.filter(
                    portrait_models.HomeVisitRecord.visited_user_id.in_(team_user_ids_subq)
                )
            else:
                # 普通 user: 仅自己
                query = query.filter(
                    portrait_models.HomeVisitRecord.visited_user_id == viewer.id
                )

        if status_filter:
            query = query.filter(portrait_models.HomeVisitRecord.status == status_filter)
        if visit_year:
            query = query.filter(portrait_models.HomeVisitRecord.visit_year == visit_year)
        if visited_ehr_id:
            target = (
                db.query(models.User)
                .filter(models.User.ehr_id == visited_ehr_id)
                .first()
            )
            if target:
                query = query.filter(
                    portrait_models.HomeVisitRecord.visited_user_id == target.id
                )

        return (
            query.order_by(portrait_models.HomeVisitRecord.visit_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_visit(
        db: Session, *, visit_id: int, viewer: models.User
    ) -> portrait_models.HomeVisitRecord:
        record = (
            db.query(portrait_models.HomeVisitRecord)
            .filter(portrait_models.HomeVisitRecord.id == visit_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"家访 {visit_id} 不存在")

        # 权限校验 (Rule 7 单一模式)
        if viewer.is_superuser:
            return record
        visited = (
            db.query(models.User)
            .filter(models.User.id == record.visited_user_id)
            .first()
        )
        if not visited:
            raise HTTPException(status_code=500, detail="家访关联用户不存在")
        if visited.team_id == viewer.team_id:
            return record
        if record.visited_user_id == viewer.id:
            return record
        raise HTTPException(status_code=403, detail="无权查看该家访")


home_visit_service = HomeVisitService()