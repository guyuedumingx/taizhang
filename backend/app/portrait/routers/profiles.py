"""
portrait /profiles 路由 (PRD A1-A5)

集成指南 §3 阶段 4: portrait P4 后端 API MVP
集成指南 §5 雷区 7: 永远走 Depends(get_current_active_user)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models  # noqa: F401 触发 ORM 注册
from app.portrait.schemas import (
    PaginatedResponse,
    PoliticalInfo,
    PoliticalInfoUpdate,
    EducationInfo,
    EducationInfoUpdate,
    FamilyInfo,
    FamilyInfoUpdate,
    ContactInfo,
    ContactInfoUpdate,
    # P0.2 新增: A4 兴趣 + A5 获奖
    InterestInfo,
    InterestInfoUpdate,
    AwardInfo,
    AwardInfoUpdate,
    # Week 2 P0.5: A1 12 卡片 - 5 张 1:N 子表
    ResumeInfo,
    ResumeInfoCreate,
    ResumeInfoUpdate,
    RewardInfo,
    RewardInfoCreate,
    RewardInfoUpdate,
    QualificationInfo,
    QualificationInfoCreate,
    QualificationInfoUpdate,
    AchievementInfo,
    AchievementInfoCreate,
    AchievementInfoUpdate,
    LanguageInfo,
    LanguageInfoCreate,
    LanguageInfoUpdate,
    # Week 3 P0.4: A11 应急先锋队标识 (admin 直改)
    EmergencyStaffUpdate,
    Profile,
    ProfileFull,
    ProfileUpdate,
)
from app.portrait.services import profile_service


router = APIRouter()


@router.get("/me", response_model=ProfileFull, summary="A1 我的档案")
def get_my_profile(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """当前用户的完整 Profile (含 12 子表)"""
    profile = profile_service.get_my_full_profile(db, viewer=current_user)
    base = ProfileFull.from_orm(profile).dict()
    base["user_name"] = current_user.name
    base["ehr_id"] = current_user.ehr_id
    base["department"] = current_user.department
    return base


@router.get("/{ehr_id}", response_model=ProfileFull, summary="按 EHR 号查档案")
def get_profile_by_ehr(
    ehr_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """按 EHR 号查 Profile (self / 同组 leader / admin 可见)"""
    target_user = (
        db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
    )
    if not target_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"用户 {ehr_id} 不存在")
    profile = profile_service.get_full_profile_by_ehr(
        db, ehr_id=ehr_id, viewer=current_user
    )
    base = ProfileFull.from_orm(profile).dict()
    base["user_name"] = target_user.name
    base["ehr_id"] = target_user.ehr_id
    base["department"] = target_user.department
    return base


@router.get("", response_model=PaginatedResponse[Profile], summary="档案列表")
def list_profiles(
    db: Session = Depends(deps.get_db),
    department: Optional[str] = Query(None, description="部门筛选 (admin only)"),
    team_id: Optional[int] = Query(None, description="团队筛选 (admin only)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> PaginatedResponse[Profile]:
    """档案列表 (admin 全员, leader 本组, user 仅自己)"""
    items = profile_service.list_profiles(
        db,
        viewer=current_user,
        department=department,
        team_id=team_id,
        skip=skip,
        limit=limit,
    )
    total = profile_service.count_profiles(
        db, viewer=current_user, department=department, team_id=team_id
    )
    return PaginatedResponse[Profile](
        items=items, total=total, page=skip // limit + 1, size=limit
    )


@router.put("/me", response_model=Profile, summary="A2 编辑基本信息 (非受保护字段)")
def update_my_profile(
    data: ProfileUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Profile:
    """更新自己 Profile 非受保护字段 (受保护字段走 profile_edit 审批)"""
    return profile_service.update_my_profile(db, viewer=current_user, data=data)


# ============================================================================
# A11 应急先锋队标识 (Week 3 P0.4) — 仅 admin 直改
# 注: PRD §5.1 原写"走 profile_edit 审批", 按用户 2026-10-10 决策改为 admin 直改。
#     路径用 /admin/users/... 前缀避开 /{ehr_id} 通配路由。
# ============================================================================
@router.put(
    "/admin/users/{target_user_id}/emergency-staff",
    response_model=Profile,
    summary="A11 设置应急先锋队标识 (仅 admin)",
)
def set_emergency_staff(
    target_user_id: int,
    data: EmergencyStaffUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Profile:
    return profile_service.set_emergency_staff(
        db,
        actor=current_user,
        target_user_id=target_user_id,
        is_emergency_staff=data.is_emergency_staff,
        reason=data.reason,
    )


@router.put("/me/political", response_model=PoliticalInfo, summary="编辑政面貌")
def update_my_political(
    data: PoliticalInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> PoliticalInfo:
    return profile_service.update_my_political(db, viewer=current_user, data=data)


@router.put("/me/education", response_model=EducationInfo, summary="编辑学历")
def update_my_education(
    data: EducationInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> EducationInfo:
    return profile_service.update_my_education(db, viewer=current_user, data=data)


@router.put("/me/family", response_model=FamilyInfo, summary="编辑家属")
def update_my_family(
    data: FamilyInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> FamilyInfo:
    return profile_service.update_my_family(db, viewer=current_user, data=data)


@router.put("/me/contact", response_model=ContactInfo, summary="编辑联系方式")
def update_my_contact(
    data: ContactInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ContactInfo:
    return profile_service.update_my_contact(db, viewer=current_user, data=data)


# P0.2 新增: A4 兴趣 + A5 获奖
@router.put("/me/interest", response_model=InterestInfo, summary="A4 编辑兴趣爱好")
def update_my_interest(
    data: InterestInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> InterestInfo:
    """A4 兴趣爱好: 兴趣名 + 熟练度 (入门/熟练/精通)"""
    return profile_service.update_my_interest(db, viewer=current_user, data=data)


@router.put("/me/award", response_model=AwardInfo, summary="A5 编辑获奖信息")
def update_my_award(
    data: AwardInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> AwardInfo:
    """A5 获奖信息: 奖项名 + 颁奖机构 + 获奖时间 + 级别 (国家级/省部级/行级)"""
    return profile_service.update_my_award(db, viewer=current_user, data=data)


# ============================================================================
# Week 2 P0.5: A1 12 卡片 - 5 张 1:N 子表 CRUD (PRD §5.1)
# 模式: POST 新建 / PUT /{id} 修改 / DELETE /{id} 删除
# ============================================================================

# --- 简历 ---
@router.post("/me/resume", response_model=ResumeInfo, summary="新增简历条目")
def add_my_resume(
    data: ResumeInfoCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ResumeInfo:
    return profile_service.add_resume(db, viewer=current_user, data=data)


@router.put("/me/resume/{item_id}", response_model=ResumeInfo, summary="修改简历条目")
def update_my_resume(
    item_id: int,
    data: ResumeInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> ResumeInfo:
    return profile_service.update_resume(db, viewer=current_user, item_id=item_id, data=data)


@router.delete("/me/resume/{item_id}", summary="删除简历条目")
def delete_my_resume(
    item_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return profile_service.delete_resume(db, viewer=current_user, item_id=item_id)


# --- 奖惩 ---
@router.post("/me/reward", response_model=RewardInfo, summary="新增奖惩条目")
def add_my_reward(
    data: RewardInfoCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> RewardInfo:
    return profile_service.add_reward(db, viewer=current_user, data=data)


@router.put("/me/reward/{item_id}", response_model=RewardInfo, summary="修改奖惩条目")
def update_my_reward(
    item_id: int,
    data: RewardInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> RewardInfo:
    return profile_service.update_reward(db, viewer=current_user, item_id=item_id, data=data)


@router.delete("/me/reward/{item_id}", summary="删除奖惩条目")
def delete_my_reward(
    item_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return profile_service.delete_reward(db, viewer=current_user, item_id=item_id)


# --- 资格 ---
@router.post("/me/qualification", response_model=QualificationInfo, summary="新增资格条目")
def add_my_qualification(
    data: QualificationInfoCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> QualificationInfo:
    return profile_service.add_qualification(db, viewer=current_user, data=data)


@router.put("/me/qualification/{item_id}", response_model=QualificationInfo, summary="修改资格条目")
def update_my_qualification(
    item_id: int,
    data: QualificationInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> QualificationInfo:
    return profile_service.update_qualification(db, viewer=current_user, item_id=item_id, data=data)


@router.delete("/me/qualification/{item_id}", summary="删除资格条目")
def delete_my_qualification(
    item_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return profile_service.delete_qualification(db, viewer=current_user, item_id=item_id)


# --- 成果 ---
@router.post("/me/achievement", response_model=AchievementInfo, summary="新增成果条目")
def add_my_achievement(
    data: AchievementInfoCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> AchievementInfo:
    return profile_service.add_achievement(db, viewer=current_user, data=data)


@router.put("/me/achievement/{item_id}", response_model=AchievementInfo, summary="修改成果条目")
def update_my_achievement(
    item_id: int,
    data: AchievementInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> AchievementInfo:
    return profile_service.update_achievement(db, viewer=current_user, item_id=item_id, data=data)


@router.delete("/me/achievement/{item_id}", summary="删除成果条目")
def delete_my_achievement(
    item_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return profile_service.delete_achievement(db, viewer=current_user, item_id=item_id)


# --- 语言 ---
@router.post("/me/language", response_model=LanguageInfo, summary="新增语言能力条目")
def add_my_language(
    data: LanguageInfoCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> LanguageInfo:
    return profile_service.add_language(db, viewer=current_user, data=data)


@router.put("/me/language/{item_id}", response_model=LanguageInfo, summary="修改语言能力条目")
def update_my_language(
    item_id: int,
    data: LanguageInfoUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> LanguageInfo:
    return profile_service.update_language(db, viewer=current_user, item_id=item_id, data=data)


@router.delete("/me/language/{item_id}", summary="删除语言能力条目")
def delete_my_language(
    item_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return profile_service.delete_language(db, viewer=current_user, item_id=item_id)