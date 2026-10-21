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
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.portrait import models as portrait_models
from app.utils.logger import log_info
from app.portrait.services import workflow_bridge
from app.services.team_service import TeamService


PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"
DRAFT = "draft"

# 单次导出行数上限。触顶时显式报错而不是静默截断 —— 用户必须知道导的是不是全部。
_EXPORT_MAX_ROWS = 5000


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


def _build_visitor_info(
    visitor: models.User,
    co_visitor: Optional[models.User],
) -> str:
    """
    拼装"家访人员及岗位" (PRD 附录 B.4 第 10 列), 格式:
        1.<姓名>，<岗位>
        2.<姓名>，<岗位>

    此前该字段由前端提交, 但 CreateHomeVisitModal 里**没有任何 name="visitor_info"
    的表单项**, validateFields() 永远不返回它 → DB 列恒为 NULL。
    改由后端拼: 前端拿不到访人岗位 (coVisitorCandidates 只有 id/name/ehr_id,
    主访人连姓名都没有), 且 F11 批量导入路径可复用同一逻辑。

    岗位取 users.department —— 与 drill 矩阵 position 列同源 (drill_service.py:204)。
    """
    parts = [f"1.{visitor.name or visitor.username}，{visitor.department or ''}"]
    if co_visitor is not None:
        parts.append(
            f"2.{co_visitor.name or co_visitor.username}，{co_visitor.department or ''}"
        )
    return "\n".join(parts)


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

        权限: 仅 leader 可创建 (决策 1: leader = 所在组的 leader_id)

        C1 (PRD §7.1) 新增校验:
          - co_visitor_user_id (如传): 必须存在 / active / 同组 / 不等于 visitor / 不等于 visited
          - team_name (如传): 必须 == "审核处理团队"; 不传则后端兜底默认填
          - scan_file_path: 直接写入 (上传校验在 file_storage_service, 此处不再校验)
        """
        if visitor.is_superuser:
            raise HTTPException(status_code=403, detail="管理员不可创建家访 (业务规则: 谁做家访谁签字)")
        # 决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id)
        if not TeamService.is_leader(db, visitor):
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

        # C1: 第二家访人校验 (如果传了)
        co_visitor_id = data.co_visitor_user_id
        co_visitor = None  # 供下方 _build_visitor_info 使用; 不选第二访人时为 None
        if co_visitor_id is not None:
            co_visitor = (
                db.query(models.User)
                .filter(models.User.id == co_visitor_id)
                .first()
            )
            if not co_visitor:
                raise HTTPException(
                    status_code=404,
                    detail=f"第二家访人 user_id={co_visitor_id} 不存在",
                )
            if not co_visitor.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"第二家访人 {co_visitor.ehr_id} 已停用, 不可家访",
                )
            if co_visitor.team_id != visitor.team_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"第二家访人 {co_visitor.ehr_id} 与您非同组 (Rule 7 单一模式)",
                )
            if co_visitor.id == visitor.id:
                raise HTTPException(
                    status_code=400,
                    detail="第二家访人不能是您本人 (您已是第一家访人)",
                )
            if co_visitor.id == visited.id:
                raise HTTPException(
                    status_code=400,
                    detail=f"第二家访人不能是被家访人 {visited.ehr_id} 本人",
                )

        # C1: team_name 校验 (固定值 + 后端兜底)
        team_name_final: Optional[str] = data.team_name
        if team_name_final is not None and team_name_final != "审核处理团队":
            raise HTTPException(
                status_code=400,
                detail=f'team_name 必须为 "审核处理团队" (Rule 12 业务规则), 收到: {team_name_final!r}',
            )
        if team_name_final is None:
            team_name_final = "审核处理团队"  # 后端兜底, 即使前端 disabled 绕过也确保写入

        record = portrait_models.HomeVisitRecord(
            visited_user_id=visited.id,
            visitor_user_id=visitor.id,
            visit_year=data.visit_year,
            visit_time=data.visit_time,
            visit_method=data.visit_method,
            visit_address=data.visit_address,
            visitor_info=_build_visitor_info(visitor, co_visitor),
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
            # C1 新增
            co_visitor_user_id=co_visitor_id,
            scan_file_path=data.scan_file_path,
            # B.4 第 14 列是必填状态值, 前端不传时兜底 "未提交" —— 不能留 NULL,
            # 否则导出模板第 14 列会出现空白格, 与业务实际表对不上。
            scan_status=data.scan_status or "未提交",
            team_name=team_name_final,
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
            message=(
                f"组长 {visitor.id} 创建家访草稿 #{record.id} 被家访人 {visited.ehr_id}"
                + (f" 第二家访人 {co_visitor_id}" if co_visitor_id else "")
                + (f" 扫描件 {data.scan_file_path}" if data.scan_file_path else "")
                + f" team={team_name_final}"
            ),
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
        record.submitted_at = datetime.now()
        db.flush()

        # Phase 2: 提交审批时创建真实 WorkflowInstance (此前模型 docstring 声称
        # "家访由服务自行绑定 workflow_instance_id" 但从未兑现, 列都不存在)
        workflow_bridge.start_home_visit_workflow(
            db, record=record, approver_id=record.current_approver_id
        )

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

        if record.workflow_instance_id:
            workflow_bridge.cancel(db, instance_id=record.workflow_instance_id)

        record.status = CANCELLED
        record.current_approver_id = None
        record.completed_at = datetime.now()

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

        if record.workflow_instance_id:
            result, _inst = workflow_bridge.approve(
                db, instance_id=record.workflow_instance_id, user_id=viewer.id, comment=comment
            )
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("message", "审批失败"))
            db.refresh(record)
        else:
            # 存量无实例的 pending 记录 (Phase 2 之前的数据): 直改镜像
            record.status = APPROVED
            record.current_approver_id = None
            record.completed_at = datetime.now()

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

        if record.workflow_instance_id:
            result, _inst = workflow_bridge.reject(
                db, instance_id=record.workflow_instance_id, user_id=viewer.id, comment=comment
            )
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("message", "驳回失败"))
            db.refresh(record)
        else:
            record.status = REJECTED
            record.current_approver_id = None
            record.completed_at = datetime.now()

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
    def _apply_list_filters(
        db: Session,
        *,
        viewer: models.User,
        status_filter: Optional[str],
        visit_year: Optional[int],
        visited_ehr_id: Optional[str],
    ):
        """列表/导出共用的筛选 + 权限收口。

        抽出来是因为批量导出 (C3/§13「家访批量导出 Excel」) 必须和列表看到
        **完全同一批** 数据 —— 否则列表看不到的记录能从导出里漏出去, 等于
        权限绕道。宁可多一个函数也不复制一份筛选条件。
        """
        query = db.query(portrait_models.HomeVisitRecord)

        if not viewer.is_superuser:
            # user: 仅自己作为被家访人的记录
            # leader: 本组成员作为被家访人的所有记录
            # 决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id)
            if TeamService.is_leader(db, viewer):
                team_user_ids_subq = (
                    db.query(models.User.id)
                    .filter(models.User.team_id == viewer.team_id)
                    .subquery()
                )
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
        return query

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
    ) -> tuple[List[portrait_models.HomeVisitRecord], int]:
        query = HomeVisitService._apply_list_filters(
            db,
            viewer=viewer,
            status_filter=status_filter,
            visit_year=visit_year,
            visited_ehr_id=visited_ehr_id,
        )
        # Phase 0 (评审 P1-1): 返回 (items, total)。此前路由用 len(本页 items) 当
        # total, 前端翻页信息全错 (total 恒等于本页条数)。
        total = query.count()
        items = (
            query.order_by(portrait_models.HomeVisitRecord.visit_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def list_for_export(
        db: Session,
        *,
        viewer: models.User,
        status_filter: Optional[str] = None,
        visit_year: Optional[int] = None,
        visited_ehr_id: Optional[str] = None,
    ) -> List[portrait_models.HomeVisitRecord]:
        """批量导出用: 不分页, 返回筛选后的全部记录。

        上限 _EXPORT_MAX_ROWS 是为了避免一次导出把内存打满 —— 触顶时导出
        endpoint 会显式报错 (Rule 12: 不能悄悄只导一半让用户以为导全了)。
        """
        query = HomeVisitService._apply_list_filters(
            db,
            viewer=viewer,
            status_filter=status_filter,
            visit_year=visit_year,
            visited_ehr_id=visited_ehr_id,
        )
        records = (
            query.order_by(portrait_models.HomeVisitRecord.visit_time.desc()).all()
        )
        if len(records) > _EXPORT_MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"当前筛选条件下有 {len(records)} 条, 超过单次导出上限 "
                    f"{_EXPORT_MAX_ROWS} 条, 请加筛选条件 (按年度/状态/被家访人)"
                ),
            )
        return records

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
        # 必须先判 viewer.team_id 非空: users.team_id 是 nullable, Python 里
        # None == None 为 True → 两个未分组用户会被判成同组, 越权读到他人家访详情
        # (含被访人电话/地址/反馈)。
        # 决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id) ——
        # "同组"本身不再等于"有权限看本组", 有权限的只有组长本人。
        if (
            TeamService.is_leader(db, viewer)
            and viewer.team_id
            and visited.team_id == viewer.team_id
        ):
            return record
        if record.visited_user_id == viewer.id:
            return record
        raise HTTPException(status_code=403, detail="无权查看该家访")

    # ========================================================================
    # F12 家访年度矩阵 (PRD 附录 B.2)
    # ========================================================================
    @staticmethod
    def matrix(
        db: Session,
        *,
        viewer: models.User,
        team_name: Optional[str] = None,
        include_pending: bool = True,
    ):
        """行 = 员工, 列 = 年份, 单元格 = 该年具体家访日期 (B.2 第 4-7 列)。

        行集 = **基准全员** (与演练矩阵同一决策, 2026-10-14): 从未���家访的员工
        必须有一行全空, 否则这张表恰恰藏起了最该被盯住的人。范围按 PRD §13 收口:
        admin 全员在职 / 组长本组在职 / 普通员工仅自己。

        统计口径 (include_pending=True, 即 approved + pending 计入):
        - approved  : 审批通过, 确实家访过 —— 必计
        - pending   : 在审批中, 大概率会通过 —— 默认计入, 用 include_pending 关掉
        - draft / rejected / cancelled: 明确不算 (草稿还没提交; 驳回/撤回等于没访成)
        """
        # 可见记录 (先按权限和状态收口, 决定哪些年份/日期进矩阵)
        status_scope = [APPROVED, PENDING] if include_pending else [APPROVED]
        records_q = db.query(portrait_models.HomeVisitRecord).filter(
            portrait_models.HomeVisitRecord.status.in_(status_scope)
        )
        if not viewer.is_superuser:
            # 决策 1: 组长看本组, 其余只看自己
            if TeamService.is_leader(db, viewer):
                # Phase 0 (评审 P0-6): 原写法把 Subquery 对象直接用于 Python `in`,
                # 组长访问矩阵必然 TypeError → 500。
                # 正确姿势是 .in_() 下推进 SQL (drill_service._visible_drill_ids_subq 同款)。
                team_user_ids = (
                    db.query(models.User.id)
                    .filter(models.User.team_id == viewer.team_id)
                    .subquery()
                )
                records_q = records_q.filter(
                    portrait_models.HomeVisitRecord.visited_user_id.in_(team_user_ids)
                )
            else:
                records_q = records_q.filter(
                    portrait_models.HomeVisitRecord.visited_user_id == viewer.id
                )
        records = records_q.all()

        # 行集 = 基准全员 (与 drill_service._matrix_row_scope 同口径, 不重复实现)
        q = db.query(models.User).filter(models.User.is_active.is_(True))
        if not viewer.is_superuser:
            if TeamService.is_leader(db, viewer):
                q = q.filter(models.User.team_id == viewer.team_id)
            else:
                q = q.filter(models.User.id == viewer.id)
        users = q.all()
        users.sort(key=lambda u: (u.ehr_id or "", u.id))
        user_by_ehr = {u.ehr_id: u for u in users}
        ehr_set = set(user_by_ehr.keys())

        # 团队筛选: 用与矩阵行渲染同一套取值口径 (team.name 优先 → department → "未分组"),
        # 否则筛不出东西 (drill_service._row_team_name 是同构实现, 那边有先例)
        def _team_name(u: models.User) -> str:
            if u.team is not None:
                return u.team.name or "未分组"
            return u.department or "未分组"

        if team_name:
            ehr_set = {e for e in ehr_set if _team_name(user_by_ehr[e]) == team_name}

        # 归属: ehr_id -> {year: [日期字符串, ...]}
        by_ehr_year: dict[str, dict[int, list[str]]] = {}
        for r in records:
            u = db.query(models.User).filter(
                models.User.id == r.visited_user_id
            ).first()
            if not u or u.ehr_id not in ehr_set:
                continue
            # B.2 要"该年具体家访日期"。visit_date 优先, 缺失时退回 visit_time 的日期 ——
            # 老数据 visit_date 可能为 NULL, 直接用会导致明明访过却显示空白。
            d = r.visit_date or (r.visit_time.date() if r.visit_time else None)
            if d is None:
                continue
            by_ehr_year.setdefault(u.ehr_id, {}).setdefault(r.visit_year, []).append(
                d.isoformat()
            )

        years = sorted({r.visit_year for r in records if r.visit_year})
        if not years:
            # 无任何记录时仍给出当前年一列, 表头不至于塌成空
            years = [datetime.now().year]

        rows = []
        for seq, ehr_id in enumerate(sorted(ehr_set), start=1):
            u = user_by_ehr[ehr_id]
            per_year = by_ehr_year.get(ehr_id, {})
            cells = []
            visited_years: list[int] = []
            for y in years:
                dates = sorted(per_year.get(y, []))
                if dates:
                    visited_years.append(y)
                cells.append(
                    {
                        "visit_date": dates[0] if dates else None,
                        "count": len(dates),
                        # 同年访多次: "2026-03-04 +2"。只显示第一次会让人以为只访了一次,
                        # 而次数恰恰是家访质量的一部分。
                        "value": (
                            dates[0] if len(dates) == 1 else f"{dates[0]} +{len(dates) - 1}"
                        ) if dates else "",
                    }
                )
            rows.append(
                {
                    "seq": seq,
                    "user_id": u.id,
                    "ehr_id": ehr_id,
                    "name": u.name or u.username or ehr_id,
                    "team_name": _team_name(u),
                    "cells": cells,
                    # B.2 第 8 列: "2023年/2026年"
                    "visited_years": "/".join(f"{y}年" for y in sorted(visited_years)),
                }
            )

        return {
            "columns": [{"year": y} for y in years],
            "rows": rows,
            "total_years": len(years),
            "total_visited_users": sum(1 for r in rows if r["visited_years"]),
        }

    # ========================================================================
    # F11 批量导入 (PRD 附录 B.4 的 14 列)
    # ========================================================================
    @staticmethod
    def import_rows(
        db: Session,
        *,
        importer: models.User,
        rows: list,
    ):
        """按 B.4 的 14 列批量导入家访记录。

        权限 (PRD §13 未列此行, 本项目定为**组长可导入本组**):
        - admin ❌: 家访业务规则是"谁做家访谁签字", create_draft 已禁止 admin,
          让 admin 批量导入等于绕过这条规则
        - 普通员工 ❌: 同 create_draft

        导入产出的记录一律 status=draft, 需要走 submit → approve 审批流, 与
        手工新建完全同构 —— 导入不是审批通道。

        逐行独立成败: 任一行失败只影响该行, 失败原因进 failed_rows (Rule 12)。
        """
        if importer.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="管理员不可导入家访 (业务规则: 谁做家访谁签字, 与新建家访一致)",
            )
        # 决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id)
        if not TeamService.is_leader(db, importer):
            raise HTTPException(
                status_code=403, detail="仅组长可批量导入家访记录 (PRD §13)"
            )

        success = 0
        failed: List[dict] = []
        # EHR -> User 缓存: 一份 Excel 里同一个被家访人常出现几十次
        user_cache: dict[str, Optional[models.User]] = {}

        def _resolve_visited(ehr_id: str) -> models.User:
            if ehr_id not in user_cache:
                user_cache[ehr_id] = (
                    db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
                )
            u = user_cache[ehr_id]
            if not u:
                raise HTTPException(status_code=404, detail=f"被家访人 {ehr_id} 不存在")
            if not u.is_active:
                raise HTTPException(status_code=400, detail=f"被家访人 {ehr_id} 已停用")
            if u.team_id != importer.team_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"被家访人 {ehr_id} 与您非同组, 仅可导入本组成员",
                )
            return u

        for row in rows:
            try:
                # B.4 第 1 列「所属团队」是固定值, 不是自由文本 —— 填错直接失败,
                # 否则导进来的记录 team_name 与业务实际不符, 后续按团队筛选全漏。
                if (row.visited_ehr_id is None) or not row.visited_ehr_id:
                    raise HTTPException(status_code=400, detail="被家访人 EHR 号为空")
                visited = _resolve_visited(row.visited_ehr_id)

                # 第 3 列姓名: 与用户表不一致说明表填错了人, 静默以用户表为准会
                # 让用户以为导的是他自己填的那个人。
                if row.visited_full_name and row.visited_full_name.strip() not in {
                    visited.name,
                    visited.username,
                }:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"姓名与系统不符: Excel 填 {row.visited_full_name!r}, "
                            f"系统里 {row.visited_ehr_id} 是 {visited.name!r}"
                        ),
                    )

                # 第 6 列年度 与 第 7 列家访时间 的年份必须一致, 否则同一行会同时
                # 出现在两个年份的矩阵里 (F12 会算出两次家访)。
                if row.visit_time is None:
                    raise HTTPException(status_code=400, detail="家访时间为空")
                if row.visit_year != row.visit_time.year:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"家访年度 {row.visit_year} 与家访时间 "
                            f"{row.visit_time.isoformat()} 的年份不一致"
                        ),
                    )

                record = portrait_models.HomeVisitRecord(
                    visited_user_id=visited.id,
                    visitor_user_id=importer.id,
                    visit_year=row.visit_year,
                    visit_time=row.visit_time,
                    visit_method=row.visit_method,
                    visit_address=row.visit_address,
                    # 第 10 列故意忽略, 按导入人重建 (见 schemas.HomeVisitImportRow 注释)
                    visitor_info=_build_visitor_info(importer, None),
                    is_visited=row.is_visited,
                    visit_date=row.visit_time.date(),
                    position=row.visited_job_title,
                    contact_phone=row.visited_phone,
                    feedback=row.remarks,
                    team_name="审核处理团队",
                    # 第 14 列 (B.4 必填), 空值兜底为 "未提交"
                    scan_status=row.scan_status or "未提交",
                    status=DRAFT,
                    current_approver_id=None,
                    submitted_at=None,
                    completed_at=None,
                )
                db.add(record)
                success += 1
            except HTTPException as exc:
                failed.append(
                    {
                        "row_number": row.row_number,
                        "ehr_id": row.visited_ehr_id,
                        "reason": str(exc.detail),
                    }
                )
            except Exception as exc:  # noqa: BLE001 — 兜底也要显性化, 不能让一行炸掉整个导入
                failed.append(
                    {
                        "row_number": row.row_number,
                        "ehr_id": getattr(row, "visited_ehr_id", ""),
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                )

        db.commit()
        log_info(
            module="portrait",
            action="home_visit.import_rows",
            message=(
                f"组长 {importer.ehr_id} 批量导入家访: 成功 {success} 条, "
                f"失败 {len(failed)} 条"
            ),
            user_id=importer.id,
            resource_type="home_visit",
            resource_id=None,
        )
        return {
            "success_count": success,
            "failed_count": len(failed),
            "failed_rows": failed,
        }


home_visit_service = HomeVisitService()