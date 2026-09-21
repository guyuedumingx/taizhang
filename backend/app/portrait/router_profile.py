"""
数字画像 · 档案读路径 API

权限模型（与 policy.csv / init_portrait_permissions 种子一致）：
  - 本人读自己：任何激活用户
  - 读他人：is_superuser 直通；或 casbin `portrait_group:read` 且与本部门(组别)一致
编辑路径（PRD §12.1 档案修改走审批流）在后续批次接入 submission 模型，本路由暂只读。
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.portrait.models import (
    AchievementInfo,
    ContactInfo,
    DevelopmentIntent,
    EducationInfo,
    FamilyInfo,
    LanguageInfo,
    Profile,
    ProfileSkillTag,
    ProjectSummary,
    QualificationInfo,
    ResumeInfo,
    RewardInfo,
    SkillTagTemplate,
)
from app.portrait.schemas import (
    AchievementInfoResponse,
    ContactInfoResponse,
    DevelopmentIntentResponse,
    EducationInfoResponse,
    FamilyInfoResponse,
    LanguageInfoResponse,
    PoliticalInfoResponse,
    ProfileBaseResponse,
    ProfileFullResponse,
    ProfileSkillTagResponse,
    ProjectSummaryResponse,
    QualificationInfoResponse,
    ResumeInfoResponse,
    RewardInfoResponse,
)

router = APIRouter()


def _can_view_profile(viewer: User, target: User) -> bool:
    """本人 / 超管 / 具 portrait_group:read 权限的同组用户"""
    if viewer.id == target.id:
        return True
    if viewer.is_superuser:
        return True
    from app.services.casbin_service import check_permission

    try:
        if not check_permission(str(viewer.id), "portrait_group", "read"):
            return False
    except Exception:
        return False
    return bool(viewer.department) and viewer.department == target.department


def _get_or_create_profile(db: Session, user_id: int) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _load_str_list(value: Optional[str]) -> List[str]:
    """发展意向的三个多选字段在库里是 JSON 字符串"""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _profile_response(db: Session, user: User) -> ProfileFullResponse:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    base = None
    if profile:
        base = ProfileBaseResponse(
            gender=profile.gender,
            nation=profile.nation,
            birth_date=profile.birth_date,
            job_title=profile.job_title,
            id_type=profile.id_type,
            id_number=profile.id_number,
            native_place=profile.native_place,
            birth_place=profile.birth_place,
            household_place=profile.household_place,
            work_start_date=profile.work_start_date,
            hire_date=profile.hire_date,
            marital_status=profile.marital_status,
            is_emergency_staff=profile.is_emergency_staff,
        )

    development_intent = None
    project_summaries: List[ProjectSummaryResponse] = []

    if profile:
        di: Optional[DevelopmentIntent] = profile.development_intent
        if di:
            development_intent = DevelopmentIntentResponse(
                id=di.id,
                profile_id=di.profile_id,
                development_path=di.development_path,
                short_term_goal=di.short_term_goal,
                mid_term_goal=di.mid_term_goal,
                core_abilities=_load_str_list(di.core_abilities),
                learning_methods=_load_str_list(di.learning_methods),
                learning_courses=di.learning_courses,
                rotation_interest=di.rotation_interest,
                rotation_target=di.rotation_target,
                project_interests=_load_str_list(di.project_interests),
                other_comments=di.other_comments,
                created_at=di.created_at,
                updated_at=di.updated_at,
            )

        summaries: List[ProjectSummary] = profile.project_summaries
        all_tag_ids = sorted({t.tag_id for p in summaries for t in p.tags})
        tag_name_map = {
            t.id: t.name
            for t in db.query(SkillTagTemplate)
            .filter(SkillTagTemplate.id.in_(all_tag_ids))
            .all()
        } if all_tag_ids else {}
        for p in summaries:
            tag_ids = [t.tag_id for t in p.tags]
            project_summaries.append(
                ProjectSummaryResponse(
                    id=p.id,
                    profile_id=p.profile_id,
                    project_name=p.project_name,
                    start_time=p.start_time,
                    end_time=p.end_time,
                    role=p.role,
                    description=p.description,
                    tag_ids=tag_ids,
                    tag_names=[tag_name_map.get(tid, "") for tid in tag_ids],
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )

    return ProfileFullResponse(
        user_id=user.id,
        ehr_no=user.ehr_id,
        name=user.name,
        group_name=user.department,
        base=base,
        political=[PoliticalInfoResponse.model_validate(x) for x in (profile.political if profile else [])],
        education=[EducationInfoResponse.model_validate(x) for x in (profile.education if profile else [])],
        family=[FamilyInfoResponse.model_validate(x) for x in (profile.family if profile else [])],
        resume=[ResumeInfoResponse.model_validate(x) for x in (profile.resume if profile else [])],
        reward=[RewardInfoResponse.model_validate(x) for x in (profile.reward if profile else [])],
        qualification=[QualificationInfoResponse.model_validate(x) for x in (profile.qualification if profile else [])],
        achievement=[AchievementInfoResponse.model_validate(x) for x in (profile.achievement if profile else [])],
        language=[LanguageInfoResponse.model_validate(x) for x in (profile.language if profile else [])],
        contact=ContactInfoResponse.model_validate(profile.contact) if profile and profile.contact else None,
        skill_tags=[ProfileSkillTagResponse.model_validate(x) for x in (profile.skill_tags if profile else [])],
        development_intent=development_intent,
        project_summaries=project_summaries,
    )


@router.get("/me", response_model=ProfileFullResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """我的档案（本人）"""
    _get_or_create_profile(db, current_user.id)
    return _profile_response(db, current_user)


@router.get("/by-ehr/{ehr_no}", response_model=ProfileFullResponse)
def get_profile_by_ehr(
    ehr_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """按 EHR 号查看他人档案（超管 / 同组 portrait_group:read）"""
    target = db.query(User).filter(User.ehr_id == ehr_no, User.is_active == True).first()  # noqa: E712
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not _can_view_profile(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有查看该档案的权限")
    _get_or_create_profile(db, target.id)
    return _profile_response(db, target)
