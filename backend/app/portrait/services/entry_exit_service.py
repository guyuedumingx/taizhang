"""
portrait 出入境台账 service (PRD §10.1 F5-F9)
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app import models
from app.core.ehr_validator import validate_ehr_format
from app.portrait import models as portrait_models
from app.portrait.schemas import entry_exit as entry_exit_schema


class EntryExitService:
    @staticmethod
    def _resolve_user(db: Session, ehr_id: str) -> models.User:
        try:
            validate_ehr_format(ehr_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"EHR号格式错误: {exc}")
        user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")
        return user

    @staticmethod
    def _can_view(viewer: models.User, target: models.User) -> bool:
        if viewer.is_superuser:
            return True
        if viewer.id == target.id:
            return True
        return bool(viewer.team_id and viewer.team_id == target.team_id)

    @staticmethod
    def list_records(
        db: Session,
        *,
        viewer: models.User,
        skip: int = 0,
        limit: int = 50,
        ehr_id: Optional[str] = None,
        name: Optional[str] = None,
        team_name: Optional[str] = None,
        year: Optional[int] = None,
    ) -> tuple[list[portrait_models.EntryExitRecord], int]:
        query = db.query(portrait_models.EntryExitRecord)
        if ehr_id:
            target = EntryExitService._resolve_user(db, ehr_id)
            if not EntryExitService._can_view(viewer, target):
                raise HTTPException(status_code=403, detail="无权查看该员工的出入境记录")
            query = query.filter(portrait_models.EntryExitRecord.user_id == target.id)
        elif not viewer.is_superuser:
            if viewer.team_id:
                team_user_ids = db.query(models.User.id).filter(models.User.team_id == viewer.team_id)
                query = query.filter(portrait_models.EntryExitRecord.user_id.in_(team_user_ids))
            else:
                query = query.filter(portrait_models.EntryExitRecord.user_id == viewer.id)

        if name:
            query = query.filter(portrait_models.EntryExitRecord.name.ilike(f"%{name}%"))
        if team_name:
            query = query.filter(portrait_models.EntryExitRecord.team_name == team_name)
        if year:
            query = query.filter(portrait_models.EntryExitRecord.year == year)

        total = query.count()
        items = (
            query.order_by(
                portrait_models.EntryExitRecord.year.desc(),
                portrait_models.EntryExitRecord.apply_depart_at.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def get_record(db: Session, *, viewer: models.User, record_id: int) -> portrait_models.EntryExitRecord:
        record = db.query(portrait_models.EntryExitRecord).filter(
            portrait_models.EntryExitRecord.id == record_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="出入境记录不存在")
        target = db.query(models.User).filter(models.User.id == record.user_id).first()
        if not target or not EntryExitService._can_view(viewer, target):
            raise HTTPException(status_code=403, detail="无权查看该出入境记录")
        return record

    @staticmethod
    def create(db: Session, *, data: entry_exit_schema.EntryExitCreate) -> portrait_models.EntryExitRecord:
        user = EntryExitService._resolve_user(db, data.ehr_id)
        record = portrait_models.EntryExitRecord(
            user_id=user.id,
            ehr_id=user.ehr_id,
            **data.model_dump(exclude={"ehr_id"}),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def update(
        db: Session,
        *,
        record: portrait_models.EntryExitRecord,
        data: entry_exit_schema.EntryExitUpdate,
    ) -> portrait_models.EntryExitRecord:
        values = data.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(record, field, value)
        # 更新后重新校验申请/实际时间顺序
        merged = entry_exit_schema.EntryExitBase(
            name=record.name,
            team_name=record.team_name,
            position=record.position,
            certificate_no=record.certificate_no,
            outbound_reason=record.outbound_reason,
            destination=record.destination,
            apply_depart_at=record.apply_depart_at,
            apply_return_at=record.apply_return_at,
            certificate_type=record.certificate_type,
            apply_type=record.apply_type,
            team_approver=record.team_approver,
            actual_depart_at=record.actual_depart_at,
            actual_return_at=record.actual_return_at,
            year=record.year,
            group_name=record.group_name,
            remark=record.remark,
        )
        del merged
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def delete(db: Session, *, record: portrait_models.EntryExitRecord) -> None:
        db.delete(record)
        db.commit()

    @staticmethod
    def statistics(db: Session, *, viewer: models.User) -> entry_exit_schema.EntryExitStatistics:
        query = db.query(portrait_models.EntryExitRecord)
        if not viewer.is_superuser:
            if viewer.team_id:
                ids = db.query(models.User.id).filter(models.User.team_id == viewer.team_id)
                query = query.filter(portrait_models.EntryExitRecord.user_id.in_(ids))
            else:
                query = query.filter(portrait_models.EntryExitRecord.user_id == viewer.id)
        current_year = datetime.now().year
        return entry_exit_schema.EntryExitStatistics(
            total_count=query.count(),
            current_year_count=query.filter(portrait_models.EntryExitRecord.year == current_year).count(),
            distinct_certificate_count=query.with_entities(
                func.count(distinct(portrait_models.EntryExitRecord.certificate_no))
            ).scalar() or 0,
            not_returned_count=query.filter(
                portrait_models.EntryExitRecord.actual_return_at.is_(None)
            ).count(),
        )

    @staticmethod
    def import_rows(
        db: Session,
        *,
        rows: list[entry_exit_schema.EntryExitImportRow],
    ) -> entry_exit_schema.EntryExitImportSummary:
        success = 0
        failed: list[dict] = []
        for row in rows:
            try:
                user = EntryExitService._resolve_user(db, row.ehr_id)
                entry = entry_exit_schema.EntryExitCreate(**row.model_dump(exclude={"row_number"}))
                db.add(portrait_models.EntryExitRecord(
                    user_id=user.id,
                    ehr_id=user.ehr_id,
                    **entry.model_dump(exclude={"ehr_id"}),
                ))
                success += 1
            except Exception as exc:
                db.rollback()
                failed.append({
                    "row_number": row.row_number,
                    "ehr_id": row.ehr_id,
                    "reason": f"{type(exc).__name__}: {exc}",
                })
        db.commit()
        return entry_exit_schema.EntryExitImportSummary(
            success_count=success,
            failed_count=len(failed),
            failed_rows=failed,
        )


entry_exit_service = EntryExitService()