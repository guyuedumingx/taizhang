"""
portrait 消防演练 service (PRD §10.2 F2-F4)
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models
from app.core.ehr_validator import validate_ehr_format
from app.portrait import models as portrait_models
from app.portrait.schemas import drill as drill_schema


def _resolve_user(db: Session, ehr_id: str) -> models.User:
    try:
        validate_ehr_format(ehr_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"EHR号格式错误: {exc}")
    user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")
    return user


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
        record = (
            db.query(portrait_models.DrillRecord)
            .filter(portrait_models.DrillRecord.id == drill_id)
            .first()
        )
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
    def matrix(db: Session, *, viewer: models.User) -> drill_schema.DrillMatrix:
        """矩阵 (F4): 行=员工, 列=每场活动, 单元格=参与状态, 紫色高亮列.
        行 = 参与过任意一场演练的员工; 单元格按列顺序对应每场活动.
        """
        drills = db.query(portrait_models.DrillRecord).order_by(
            portrait_models.DrillRecord.activity_date.asc()
        ).all()
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

        # 涉及员工: 按 ehr_id 去重, 再查询 User 取团队信息
        ehr_set: set[str] = set()
        for did in drill_ids:
            ehr_set.update(participation[did].keys())
        users = (
            db.query(models.User)
            .filter(models.User.ehr_id.in_(ehr_set))
            .all()
        ) if ehr_set else []
        user_by_ehr = {u.ehr_id: u for u in users}

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
                team_name=(u.team.name if u and u.team else (u.department if u else "")) or "未分组",
                position=u.department if u else "",
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
            total_participants=len(ehr_set),
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