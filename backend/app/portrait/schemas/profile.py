"""
portrait Profile + 9 子表的 Pydantic schema

字段严格对齐 app/portrait/models/profile.py 的列定义 (Rule 8 先读再写)
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# ============================================================================
# Profile 主表
# ============================================================================
class ProfileBase(BaseModel):
    gender: Optional[str] = None
    nation: Optional[str] = None
    birth_date: Optional[date] = None
    job_title: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    native_place: Optional[str] = None
    birth_place: Optional[str] = None
    household_place: Optional[str] = None
    work_start_date: Optional[date] = None
    hire_date: Optional[date] = None
    marital_status: Optional[str] = None
    is_emergency_staff: bool = False


class ProfileCreate(ProfileBase):
    """创建 Profile (MVP 阶段: 暂不开放创建, 走用户元数据同步)"""
    user_id: int


class ProfileUpdate(BaseModel):
    """更新 Profile 用的部分字段 (Rule 3: 只暴露可改字段)"""
    gender: Optional[str] = None
    nation: Optional[str] = None
    birth_date: Optional[date] = None
    job_title: Optional[str] = None
    native_place: Optional[str] = None
    birth_place: Optional[str] = None
    household_place: Optional[str] = None
    work_start_date: Optional[date] = None
    hire_date: Optional[date] = None
    marital_status: Optional[str] = None
    # 注: id_type/id_number/is_emergency_staff 走 profile_edit 审批, 不直接 PUT


class ProfileInDBBase(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Profile(ProfileInDBBase):
    """返回给 API 的 Profile (含子表汇总字段)"""
    user_name: Optional[str] = None
    ehr_id: Optional[str] = None
    department: Optional[str] = None


# ============================================================================
# 9 个子表
# ============================================================================
class PoliticalInfoBase(BaseModel):
    political_status: Optional[str] = None
    join_date: Optional[date] = None
    introducer: Optional[str] = None


class PoliticalInfoCreate(PoliticalInfoBase):
    pass


class PoliticalInfoUpdate(PoliticalInfoBase):
    pass


class PoliticalInfo(PoliticalInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class EducationInfoBase(BaseModel):
    education_category: Optional[str] = None
    education_type: Optional[str] = None
    education_level: Optional[str] = None
    degree: Optional[str] = None
    school: Optional[str] = None
    major_name: Optional[str] = None
    duration_years: Optional[str] = None
    enrollment_date: Optional[date] = None
    graduation_date: Optional[date] = None
    completion_status: Optional[str] = None
    country: Optional[str] = None


class EducationInfoCreate(EducationInfoBase):
    pass


class EducationInfoUpdate(EducationInfoBase):
    pass


class EducationInfo(EducationInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class FamilyInfoBase(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    relation: Optional[str] = None
    birth_date: Optional[date] = None
    work_unit_and_title: Optional[str] = None
    political_status: Optional[str] = None
    employment_status: Optional[str] = None


class FamilyInfoCreate(FamilyInfoBase):
    pass


class FamilyInfoUpdate(FamilyInfoBase):
    pass


class FamilyInfo(FamilyInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class ResumeInfoBase(BaseModel):
    start_time: Optional[date] = None
    end_time: Optional[date] = None
    unit_and_title: Optional[str] = None


class ResumeInfoCreate(ResumeInfoBase):
    pass


class ResumeInfoUpdate(ResumeInfoBase):
    pass


class ResumeInfo(ResumeInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class RewardInfoBase(BaseModel):
    reward_type: Optional[str] = None
    reward_time: Optional[date] = None
    reward_name: Optional[str] = None
    reward_reason: Optional[str] = None


class RewardInfoCreate(RewardInfoBase):
    pass


class RewardInfoUpdate(RewardInfoBase):
    pass


class RewardInfo(RewardInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class QualificationInfoBase(BaseModel):
    qualification_name: Optional[str] = None
    obtain_time: Optional[date] = None
    valid_until: Optional[date] = None


class QualificationInfoCreate(QualificationInfoBase):
    pass


class QualificationInfoUpdate(QualificationInfoBase):
    pass


class QualificationInfo(QualificationInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class AchievementInfoBase(BaseModel):
    achievement_name: Optional[str] = None
    obtain_time: Optional[date] = None


class AchievementInfoCreate(AchievementInfoBase):
    pass


class AchievementInfoUpdate(AchievementInfoBase):
    pass


class AchievementInfo(AchievementInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class LanguageInfoBase(BaseModel):
    language: Optional[str] = None
    proficiency: Optional[str] = None
    cert_level_or_score: Optional[str] = None


class LanguageInfoCreate(LanguageInfoBase):
    pass


class LanguageInfoUpdate(LanguageInfoBase):
    pass


class LanguageInfo(LanguageInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


class ContactInfoBase(BaseModel):
    mobile: Optional[str] = None
    office_phone: Optional[str] = None
    home_phone: Optional[str] = None
    home_address: Optional[str] = None
    email: Optional[str] = None
    commute_minutes: Optional[int] = None


class ContactInfoCreate(ContactInfoBase):
    pass


class ContactInfoUpdate(ContactInfoBase):
    pass


class ContactInfo(ContactInfoBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


# ============================================================================
# 组合响应: Profile + 9 子表 (前端 A1 个人档案首页用)
# ============================================================================
class ProfileFull(Profile):
    """完整 Profile + 9 子表 (A1 个人档案首页 / B4 详情页用)"""
    political: List[PoliticalInfo] = []
    education: List[EducationInfo] = []
    family: List[FamilyInfo] = []
    resume: List[ResumeInfo] = []
    reward: List[RewardInfo] = []
    qualification: List[QualificationInfo] = []
    achievement: List[AchievementInfo] = []
    language: List[LanguageInfo] = []
    contact: Optional[ContactInfo] = None
    skill_tag_names: List[str] = []  # 来自 ProfileSkillTag


# ============================================================================
# 列表查询参数
# ============================================================================
class ProfileListQuery(BaseModel):
    """列表查询参数 (Pydantic v1 用作依赖项, 实际在 router 用 Query())"""
    department: Optional[str] = None
    team_id: Optional[int] = None
    skip: int = 0
    limit: int = 50