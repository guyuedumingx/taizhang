"""
portrait 培训记录 service (PRD §10.3 占位)

业务规则:
  - 员工只能读自己的培训记录 (D2)
  - 管理员/组长可读本组员 (跨组 403, 与 profile 一致)
  - 管理员可批量导入
  - 个人不提供新建 (占位阶段, 数据走批量导入或管理员录入)
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.core.ehr_validator import validate_ehr_format
from app.portrait import models as portrait_models
from app.portrait.schemas import training as training_schema


def _can_view_training(viewer: models.User, target_user: models.User) -> bool:
    """与 profile_service._can_view_profile 一致 (Rule 7 单一模式)"""
    if viewer.is_superuser:
        return True
    if viewer.team_id and viewer.team_id == target_user.team_id:
        return True
    if viewer.id == target_user.id:
        return True
    return False


def _resolve_user_by_ehr(db: Session, ehr_id: str) -> models.User:
    """根据 EHR 号查找用户. EHR 格式校验失败抛 401, 用户不存在抛 404."""
    try:
        validate_ehr_format(ehr_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"EHR号格式错误: {e}")

    user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")
    return user


class TrainingService:
    @staticmethod
    def list_for_user(db: Session, *, viewer: models.User, user_id: int) -> List[portrait_models.TrainingRecord]:
        """按 user_id 列培训记录. 权限: 仅本人/本组/admin"""
        target_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not _can_view_training(viewer, target_user):
            raise HTTPException(status_code=403, detail="无权查看该用户的培训记录")
        return (
            db.query(portrait_models.TrainingRecord)
            .filter(portrait_models.TrainingRecord.user_id == user_id)
            .order_by(portrait_models.TrainingRecord.training_at.desc())
            .all()
        )

    @staticmethod
    def list_by_ehr(db: Session, *, viewer: models.User, ehr_id: str) -> List[portrait_models.TrainingRecord]:
        """按 EHR 列培训记录 (PRD D2: 跨人查看)"""
        target_user = _resolve_user_by_ehr(db, ehr_id)
        return TrainingService.list_for_user(db, viewer=viewer, user_id=target_user.id)

    @staticmethod
    def create(db: Session, *, data: training_schema.TrainingRecordCreate) -> portrait_models.TrainingRecord:
        """管理员录入单条 (D1 占位阶段用于管理员手动补录)"""
        user = _resolve_user_by_ehr(db, data.ehr_id)
        record = portrait_models.TrainingRecord(
            user_id=user.id,
            ehr_id=user.ehr_id,
            training_name=data.training_name,
            training_at=data.training_at,
            training_type=data.training_type,
            institution=data.institution,
            certificate_no=data.certificate_no,
            valid_until=data.valid_until,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def import_rows(
        db: Session,
        *,
        rows: List[training_schema.TrainingImportRow],
    ) -> training_schema.TrainingImportSummary:
        """批量导入: 每行校验 EHR, 用户不存在则记录失败, 否则写入.
        Rule 12: 失败显性化, 每条错误都返回给调用方.
        """
        success = 0
        failed: list[dict] = []

        for row in rows:
            try:
                # EHR 格式校验
                try:
                    validate_ehr_format(row.ehr_id)
                except ValueError as e:
                    failed.append({
                        "row_number": row.row_number,
                        "ehr_id": row.ehr_id,
                        "reason": f"EHR号格式错误: {e}",
                    })
                    continue

                user = (
                    db.query(models.User)
                    .filter(models.User.ehr_id == row.ehr_id)
                    .first()
                )
                if not user:
                    failed.append({
                        "row_number": row.row_number,
                        "ehr_id": row.ehr_id,
                        "reason": f"EHR号 {row.ehr_id} 对应用户不存在",
                    })
                    continue

                record = portrait_models.TrainingRecord(
                    user_id=user.id,
                    ehr_id=user.ehr_id,
                    training_name=row.training_name,
                    training_at=row.training_at,
                    training_type=row.training_type,
                    institution=row.institution,
                    certificate_no=row.certificate_no,
                    valid_until=row.valid_until,
                )
                db.add(record)
                success += 1
            except Exception as e:  # 行级异常: 不让一行拖垮整批
                failed.append({
                    "row_number": row.row_number,
                    "ehr_id": row.ehr_id,
                    "reason": f"行处理异常: {type(e).__name__}: {e}",
                })

        db.commit()
        return training_schema.TrainingImportSummary(
            success_count=success,
            failed_count=len(failed),
            failed_rows=failed,
        )


training_service = TrainingService()