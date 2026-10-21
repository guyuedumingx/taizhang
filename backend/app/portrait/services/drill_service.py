"""
portrait 消防演练 service (PRD §10.2 F2-F4)
"""
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models
from app.core.ehr_validator import validate_ehr_format
from app.portrait import models as portrait_models
from app.portrait.schemas import drill as drill_schema
from app.services.team_service import TeamService


def _resolve_user(db: Session, ehr_id: str) -> models.User:
    try:
        validate_ehr_format(ehr_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"EHR号格式错误: {exc}")
    user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")
    return user


def _visible_drill_ids_subq(db: Session, viewer: models.User):
    """
    PRD §13 消防演练(看): 员工仅自己 / 组长本组 / 管理员全员。
    返回"可见 drill_id"的子查询; admin 返回 None 表示**不过滤**。

    此前 list_records / get_detail / matrix 三个函数虽然都声明了 viewer 参数,
    但函数体一次都没用过它 —— 三处都是全表直查, 任意登录员工可见全部演练
    记录与参与人。判定语义与 profile_service._can_view_profile 一致
    (admin → 全员; 组长 → 本组; 本人 → 自己)。

    决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id),
    旧判据 "有 team_id 即组长" 让任何员工分到组就获得组长权限。
    """
    if viewer.is_superuser:
        return None
    part = portrait_models.DrillParticipant
    if TeamService.is_leader(db, viewer):
        # 组长: 本组任一员工作为参与者参与过的演练
        team_user_ids = (
            db.query(models.User.id)
            .filter(models.User.team_id == viewer.team_id)
            .subquery()
        )
        return db.query(part.drill_id).filter(part.user_id.in_(team_user_ids))
    # 普通员工: 自己参与过的演练
    return db.query(part.drill_id).filter(part.user_id == viewer.id)


def _row_team_name(u: Optional[models.User]) -> str:
    """矩阵行的团队名取值口径。抽成函数是为了让筛选与渲染用同一套规则。"""
    if u is None:
        return "未分组"
    if u.team is not None:
        return u.team.name or "未分组"
    return u.department or "未分组"


def _matrix_row_scope(db: Session, viewer: models.User) -> list[models.User]:
    """矩阵行集范围 (PRD §13 + 附录 B.1「全员 × 全部活动」)。

    "全员"不是全行 —— 必须按查看者权限收口, 否则 admin 之外的人会看到全公司
    1494 人的演练参与情况 (ehr_id + 姓名 + 每场是否参加), 这是彻底的越权。

    admin → 全行在职; 组长 → 本组在职; 普通员工 → 仅自己。
    停用账号 (is_active=False) 排除: 已停用的人恒为"未参加", 只会污染考核口径。
    """
    q = db.query(models.User).filter(models.User.is_active.is_(True))
    if viewer.is_superuser:
        return q.all()
    if TeamService.is_leader(db, viewer):
        return q.filter(models.User.team_id == viewer.team_id).all()
    return q.filter(models.User.id == viewer.id).all()


class DrillService:
    # --------------------------------------------------------------------- F2 演练登记
    @staticmethod
    def create(
        db: Session,
        *,
        data: drill_schema.DrillCreate,
    ) -> portrait_models.DrillRecord:
        record = portrait_models.DrillRecord(
            activity_date=data.activity_date,
            drill_type=data.drill_type,
            location=data.location,
            duration_minutes=data.duration_minutes,
        )
        db.add(record)
        db.flush()  # 拿到 record.id

        # Rule 12: 先一次性校验所有参与者, 任一无效 EHR 立即报错 (不静默跳过)
        invalid = []
        resolved: list[models.User] = []
        for ehr_id in data.participant_ehr_ids:
            try:
                resolved.append(_resolve_user(db, ehr_id))
            except HTTPException as exc:
                invalid.append({"ehr_id": ehr_id, "reason": str(exc.detail)})
        if invalid:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"存在无效参与人员: {invalid}")

        for user in resolved:
            db.add(portrait_models.DrillParticipant(
                drill_id=record.id,
                user_id=user.id,
                ehr_id=user.ehr_id,
                name=user.name,
                participated=True,  # F2 登记即视为已参与
            ))
        db.commit()
        db.refresh(record)
        setattr(record, "_participant_count", len(resolved))
        return record

    # --------------------------------------------------------------------- 列表
    @staticmethod
    def list_records(
        db: Session,
        *,
        viewer: models.User,
        skip: int = 0,
        limit: int = 50,
        drill_type: Optional[str] = None,
        team_name: Optional[str] = None,
    ):
        query = db.query(portrait_models.DrillRecord)
        visible = _visible_drill_ids_subq(db, viewer)
        if visible is not None:
            query = query.filter(portrait_models.DrillRecord.id.in_(visible))
        if drill_type:
            query = query.filter(portrait_models.DrillRecord.drill_type == drill_type)

        # 团队筛选: 通过参与人员 join users
        if team_name:
            query = query.join(
                portrait_models.DrillParticipant,
                portrait_models.DrillParticipant.drill_id
                == portrait_models.DrillRecord.id,
            ).join(models.User, models.User.id == portrait_models.DrillParticipant.user_id)
            query = query.filter(models.User.department == team_name)
            query = query.distinct()

        total = query.count()
        records = (
            query.order_by(portrait_models.DrillRecord.activity_date.desc())
            .offset(skip).limit(limit)
            .all()
        )

        # 参与人数
        for record in records:
            count = (
                db.query(func.count(portrait_models.DrillParticipant.id))
                .filter(portrait_models.DrillParticipant.drill_id == record.id)
                .scalar() or 0
            )
            setattr(record, "_participant_count", count)
        return records, total

    @staticmethod
    def get_detail(
        db: Session,
        *,
        viewer: models.User,
        drill_id: int,
    ) -> portrait_models.DrillRecord:
        query = db.query(portrait_models.DrillRecord).filter(
            portrait_models.DrillRecord.id == drill_id
        )
        visible = _visible_drill_ids_subq(db, viewer)
        if visible is not None:
            query = query.filter(portrait_models.DrillRecord.id.in_(visible))
        # 不可见时走 404 而非 403: 不泄露"该演练是否存在"
        record = query.first()
        if not record:
            raise HTTPException(status_code=404, detail="演练记录不存在")
        count = (
            db.query(func.count(portrait_models.DrillParticipant.id))
            .filter(portrait_models.DrillParticipant.drill_id == drill_id)
            .scalar() or 0
        )
        setattr(record, "_participant_count", count)
        setattr(
            record,
            "_participants",
            db.query(portrait_models.DrillParticipant)
            .filter(portrait_models.DrillParticipant.drill_id == drill_id)
            .all(),
        )
        return record

    @staticmethod
    def delete(db: Session, *, drill_id: int) -> None:
        record = db.query(portrait_models.DrillRecord).filter(
            portrait_models.DrillRecord.id == drill_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="演练记录不存在")
        db.query(portrait_models.DrillParticipant).filter(
            portrait_models.DrillParticipant.drill_id == drill_id
        ).delete(synchronize_session=False)
        db.delete(record)
        db.commit()

    # --------------------------------------------------------------------- F4 矩阵
    @staticmethod
    def matrix(
        db: Session,
        *,
        viewer: models.User,
        year: Optional[int] = None,
        team_name: Optional[str] = None,
    ) -> drill_schema.DrillMatrix:
        """矩阵 (F4): 行=员工, 列=每场活动, 单元格=参与状态, 紫色高亮列.

        行集 = **基准全员**(PRD 附录 B.1「全员 × 全部活动」), 每人一行, 从未
        参加过的一行全是"未参与"。此前行集是从参与记录反推的, 零参加者根本不
        出现在表里 —— 而 §10.2.3 说这张表的用途正是"一眼看到谁参与度低", 最该
        被盯住的那批人反而被隐藏了。(2026-10-14 用户决定改为全员基准行)

        ⚠️ "全员"是相对**该查看者有权看的人**: admin=全行在职, 组长=本组,
        普通员工=仅自己。详见 _matrix_row_scope()。
        """
        query = db.query(portrait_models.DrillRecord)
        visible = _visible_drill_ids_subq(db, viewer)
        if visible is not None:
            query = query.filter(portrait_models.DrillRecord.id.in_(visible))
        if year is not None:
            # activity_date 是 Date 列; SQLite 无 strftime 的 ORM 封装, 用范围比较更稳
            start = date(year, 1, 1)
            end = date(year, 12, 31)
            query = query.filter(
                portrait_models.DrillRecord.activity_date >= start,
                portrait_models.DrillRecord.activity_date <= end,
            )
        drills = query.order_by(portrait_models.DrillRecord.activity_date.asc()).all()
        drill_ids = [d.id for d in drills]

        # participation: {drill_id: {ehr_id: participated}}
        participation: dict[int, dict[str, bool]] = {did: {} for did in drill_ids}
        if drill_ids:
            participants = (
                db.query(portrait_models.DrillParticipant)
                .filter(portrait_models.DrillParticipant.drill_id.in_(drill_ids))
                .all()
            )
            for p in participants:
                participation.setdefault(p.drill_id, {})[p.ehr_id] = p.participated

        # 行集 = 基准全员 (不再从参与记录反推)。范围按 §13 收口到该查看者有权看的人:
        # admin 全行在职 / 组长本组 / 普通员工仅自己。停用账号不计入 —— 已离职的人
        # 记为"未参加"没有意义, 只会污染考核口径。
        users = _matrix_row_scope(db, viewer)
        user_by_ehr = {u.ehr_id: u for u in users}
        ehr_set = set(user_by_ehr.keys())

        # 团队筛选: 与下方 rows 里 team_name 的取值口径保持一致 (team.name 优先,
        # 回落 department, 再回落 "未分组"), 否则筛不出东西。
        if team_name:
            ehr_set = {
                e for e in ehr_set
                if _row_team_name(user_by_ehr.get(e)) == team_name
            }

        rows = []
        for ehr_id in sorted(ehr_set):
            u = user_by_ehr.get(ehr_id)
            cells = []
            participated_count = 0
            for did in drill_ids:
                participated = bool(participation[did].get(ehr_id, False))
                if participated:
                    participated_count += 1
                cells.append(drill_schema.MatrixCell(
                    participated=participated,
                    value="参与" if participated else "未参与",
                ))
            rows.append(drill_schema.MatrixRow(
                user_id=u.id if u else 0,
                ehr_id=ehr_id,
                name=u.name if u else ehr_id,
                team_name=_row_team_name(u),
                position=(u.department or "") if u else "",
                cells=cells,
                participated_count=participated_count,
            ))

        return drill_schema.DrillMatrix(
            columns=[
                {
                    "drill_id": d.id,
                    "activity_date": d.activity_date.isoformat(),
                    "drill_type": d.drill_type,
                    "location": d.location,
                }
                for d in drills
            ],
            rows=rows,
            total_drills=len(drills),
            # rows 现在是"基准全员", 参与人数需单独统计, 否则该字段会变成
            # "矩阵里有多少行" (= 全员数), 前端"涉及 N 名员工"就会误导。
            total_participants=sum(1 for r in rows if r.participated_count > 0),
        )

    # --------------------------------------------------------------------- F3 批量导入
    @staticmethod
    def import_rows(
        db: Session,
        *,
        rows: list[drill_schema.DrillImportRow],
    ) -> drill_schema.DrillImportSummary:
        """批量导入 (6 列): 同一活动日期+类型+地点 归并为一条 DrillRecord,
        每行一个参与者. 重复 (drill_date, ehr) 去重.
        """
        success = 0
        failed: list[dict] = []

        # 归并活动: key = (activity_date, drill_type, location)
        drill_cache: dict[tuple, portrait_models.DrillRecord] = {}

        for row in rows:
            try:
                user = _resolve_user(db, row.ehr_id)
            except Exception as exc:
                failed.append({
                    "row_number": row.row_number,
                    "ehr_id": row.ehr_id,
                    "reason": f"{type(exc).__name__}: {exc}",
                })
                continue

            key = (row.activity_date, row.drill_type, row.location)
            drill = drill_cache.get(key)
            if drill is None:
                drill = (
                    db.query(portrait_models.DrillRecord)
                    .filter(
                        portrait_models.DrillRecord.activity_date == row.activity_date,
                        portrait_models.DrillRecord.drill_type == row.drill_type,
                        portrait_models.DrillRecord.location == row.location,
                    )
                    .first()
                )
                if drill is None:
                    drill = portrait_models.DrillRecord(
                        activity_date=row.activity_date,
                        drill_type=row.drill_type,
                        location=row.location,
                    )
                    db.add(drill)
                    db.flush()
                drill_cache[key] = drill

            # 去重: 同一 (drill_id, ehr_id)
            exists = (
                db.query(portrait_models.DrillParticipant.id)
                .filter(
                    portrait_models.DrillParticipant.drill_id == drill.id,
                    portrait_models.DrillParticipant.ehr_id == user.ehr_id,
                )
                .first()
            )
            if exists:
                failed.append({
                    "row_number": row.row_number,
                    "ehr_id": row.ehr_id,
                    "reason": "该员工已在此活动中, 跳过重复",
                })
                continue

            db.add(portrait_models.DrillParticipant(
                drill_id=drill.id,
                user_id=user.id,
                ehr_id=user.ehr_id,
                name=user.name,
                participated=row.participated,
            ))
            success += 1

        db.commit()
        return drill_schema.DrillImportSummary(
            success_count=success,
            failed_count=len(failed),
            failed_rows=failed,
        )


drill_service = DrillService()