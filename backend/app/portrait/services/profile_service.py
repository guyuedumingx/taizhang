"""
portrait Profile service

集成指南 §3 阶段 4: portrait P4 后端 API MVP
集成指南 §5 雷区合规:
  - 1. 不改 rbac_model.conf (走 policy.csv)
  - 7. 不绕过 Depends (业务层强制校验, 失败抛 HTTPException)

权限模型 (Rule 7: 单一模式, Python 显式判断, 不混 Casbin):
  - admin / is_superuser : 看全部
  - leader : 看本组 (User.team_id 相等)
  - user   : 只看自己 (User.id 相等)
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app import models
from app.portrait import models as portrait_models
from app.portrait.schemas import profile as profile_schema


def _can_view_profile(viewer: models.User, profile_user: models.User) -> bool:
    """判定 viewer 能否查看 profile_user 的档案
    Rule 7: 单一模式, Python 显式判断, 不混 Casbin
    """
    if viewer.is_superuser:
        return True
    if viewer.team_id and viewer.team_id == profile_user.team_id:
        return True
    if viewer.id == profile_user.id:
        return True
    return False


def _ensure_can_view(viewer: models.User, profile_user: models.User) -> None:
    if not _can_view_profile(viewer, profile_user):
        raise HTTPException(status_code=403, detail=f"无权查看用户 {profile_user.ehr_id} 的档案")


def _get_or_create_profile(db: Session, user: models.User) -> portrait_models.Profile:
    """获取 Profile, 不存在则自动创建 (空档案)"""
    profile = (
        db.query(portrait_models.Profile)
        .filter(portrait_models.Profile.user_id == user.id)
        .first()
    )
    if profile:
        return profile
    profile = portrait_models.Profile(user_id=user.id)
    db.add(profile)
    db.flush()
    return profile


class ProfileService:
    """Profile 业务服务"""

    @staticmethod
    def get_full_profile_by_ehr(
        db: Session, *, ehr_id: str, viewer: models.User
    ) -> portrait_models.Profile:
        """按 EHR 号查完整 Profile + 9 子表"""
        target_user = (
            db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        )
        if not target_user:
            raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")

        _ensure_can_view(viewer, target_user)

        profile = (
            db.query(portrait_models.Profile)
            .options(
                selectinload(portrait_models.Profile.political),
                selectinload(portrait_models.Profile.education),
                selectinload(portrait_models.Profile.family),
                selectinload(portrait_models.Profile.resume),
                selectinload(portrait_models.Profile.reward),
                selectinload(portrait_models.Profile.qualification),
                selectinload(portrait_models.Profile.achievement),
                selectinload(portrait_models.Profile.language),
                selectinload(portrait_models.Profile.contact),
                selectinload(portrait_models.Profile.skill_tags),
            )
            .filter(portrait_models.Profile.user_id == target_user.id)
            .first()
        )
        if not profile:
            # 自动建空档案, 方便前端展示
            profile = _get_or_create_profile(db, target_user)
            db.commit()
            db.refresh(profile)

        # 把 user 基础信息 attach 到 profile 上 (前端展示用, router 层读 _xxx)
        profile._user_name = target_user.name
        profile._ehr_id = target_user.ehr_id
        profile._department = target_user.department
        return profile

    @staticmethod
    def get_my_full_profile(db: Session, *, viewer: models.User) -> portrait_models.Profile:
        """获取当前用户自己的完整 Profile"""
        return ProfileService.get_full_profile_by_ehr(
            db, ehr_id=viewer.ehr_id, viewer=viewer
        )

    @staticmethod
    def list_profiles(
        db: Session,
        *,
        viewer: models.User,
        department: Optional[str] = None,
        team_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[portrait_models.Profile]:
        """档案列表 (admin 全员 / leader 本组 / user 仅自己)"""
        query = db.query(portrait_models.Profile).join(
            models.User, models.User.id == portrait_models.Profile.user_id
        )

        if viewer.is_superuser:
            # admin: 可按 department / team_id 筛选
            if department:
                query = query.filter(models.User.department == department)
            if team_id:
                query = query.filter(models.User.team_id == team_id)
        elif viewer.team_id:
            # leader: 仅本组
            query = query.filter(models.User.team_id == viewer.team_id)
        else:
            # user: 仅自己
            query = query.filter(models.User.id == viewer.id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count_profiles(
        db: Session,
        *,
        viewer: models.User,
        department: Optional[str] = None,
        team_id: Optional[int] = None,
    ) -> int:
        """统计数量 (跟 list_profiles 同步筛选)"""
        query = db.query(portrait_models.Profile).join(
            models.User, models.User.id == portrait_models.Profile.user_id
        )

        if viewer.is_superuser:
            if department:
                query = query.filter(models.User.department == department)
            if team_id:
                query = query.filter(models.User.team_id == team_id)
        elif viewer.team_id:
            query = query.filter(models.User.team_id == viewer.team_id)
        else:
            query = query.filter(models.User.id == viewer.id)

        return query.count()

    # ========================================================================
    # PUT 自己 (仅非受保护字段, 受保护字段走 profile_edit 审批)
    # ========================================================================
    @staticmethod
    def update_my_profile(
        db: Session,
        *,
        viewer: models.User,
        data: profile_schema.ProfileUpdate,
    ) -> portrait_models.Profile:
        """更新自己 Profile 的非受保护字段"""
        profile = _get_or_create_profile(db, viewer)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        return profile

    # ========================================================================
    # 子表更新 (按子表)
    # ========================================================================
    @staticmethod
    def _upsert_single_subtable(
        db: Session,
        *,
        profile: portrait_models.Profile,
        model_cls,
        data,
    ):
        """单条子表的 upsert (MVP 简化版: 仅保留最新一条)"""
        existing = (
            db.query(model_cls).filter(model_cls.profile_id == profile.id).first()
        )
        if existing:
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            obj = model_cls(profile_id=profile.id, **data.model_dump())
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj

    @staticmethod
    def update_my_political(
        db: Session,
        *,
        viewer: models.User,
        data: profile_schema.PoliticalInfoUpdate,
    ):
        profile = _get_or_create_profile(db, viewer)
        return ProfileService._upsert_single_subtable(
            db, profile=profile, model_cls=portrait_models.PoliticalInfo, data=data
        )

    @staticmethod
    def update_my_education(
        db: Session,
        *,
        viewer: models.User,
        data: profile_schema.EducationInfoUpdate,
    ):
        profile = _get_or_create_profile(db, viewer)
        return ProfileService._upsert_single_subtable(
            db, profile=profile, model_cls=portrait_models.EducationInfo, data=data
        )

    @staticmethod
    def update_my_family(
        db: Session,
        *,
        viewer: models.User,
        data: profile_schema.FamilyInfoUpdate,
    ):
        profile = _get_or_create_profile(db, viewer)
        return ProfileService._upsert_single_subtable(
            db, profile=profile, model_cls=portrait_models.FamilyInfo, data=data
        )

    @staticmethod
    def update_my_contact(
        db: Session,
        *,
        viewer: models.User,
        data: profile_schema.ContactInfoUpdate,
    ):
        profile = _get_or_create_profile(db, viewer)
        return ProfileService._upsert_single_subtable(
            db, profile=profile, model_cls=portrait_models.ContactInfo, data=data
        )


# 暴露单例
profile_service = ProfileService()