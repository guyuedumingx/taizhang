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
    """当前用户的完整 Profile (含 9 子表)"""
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