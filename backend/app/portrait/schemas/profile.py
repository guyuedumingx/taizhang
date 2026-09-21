"""
数字画像 · 档案响应 Schema

字段名与数字画像原版保持一致（前端可平移），仅两个顶层映射：
  ehr_no     <- taizhang users.ehr_id
  group_name <- taizhang users.department  (画像"组别" = 台账部门字段)
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# ----- 基础信息 -----
class ProfileBaseResponse(BaseModel):
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
    is_emergency_staff: Optional[bool] = None


# ----- 子表响应 -----
class PoliticalInfoResponse(BaseModel):
    id: int
    profile_id: int
    political_status: Optional[str] = None
    join_date: Optional[date] = None
    introducer: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EducationInfoResponse(BaseModel):
    id: int
    profile_id: int
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FamilyInfoResponse(BaseModel):
    id: int
    profile_id: int
    name: Optional[str] = None
    gender: Optional[str] = None
    relation: Optional[str] = None
    birth_date: Optional[date] = None
    work_unit_and_title: Optional[str] = None
    political_status: Optional[str] = None
    employment_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeInfoResponse(BaseModel):
    id: int
    profile_id: int
    start_time: Optional[date] = None
    end_time: Optional[date] = None
    unit_and_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RewardInfoResponse(BaseModel):
    id: int
    profile_id: int
    reward_type: Optional[str] = None
    reward_time: Optional[date] = None
    reward_name: Optional[str] = None
    reward_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QualificationInfoResponse(BaseModel):
    id: int
    profile_id: int
    qualification_name: Optional[str] = None
    obtain_time: Optional[date] = None
    valid_until: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AchievementInfoResponse(BaseModel):
    id: int
    profile_id: int
    achievement_name: Optional[str] = None
    obtain_time: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LanguageInfoResponse(BaseModel):
    id: int
    profile_id: int
    language: Optional[str] = None
    proficiency: Optional[str] = None
    cert_level_or_score: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactInfoResponse(BaseModel):
    id: int
    profile_id: int
    mobile: Optional[str] = None
    office_phone: Optional[str] = None
    home_phone: Optional[str] = None
    home_address: Optional[str] = None
    email: Optional[str] = None
    commute_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileSkillTagResponse(BaseModel):
    id: int
    profile_id: int
    tag_name: str
    template_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DevelopmentIntentResponse(BaseModel):
    id: int
    profile_id: int
    development_path: Optional[str] = None
    short_term_goal: Optional[str] = None
    mid_term_goal: Optional[str] = None
    core_abilities: List[str] = []
    learning_methods: List[str] = []
    learning_courses: Optional[str] = None
    rotation_interest: Optional[str] = None
    rotation_target: Optional[str] = None
    project_interests: List[str] = []
    other_comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectSummaryResponse(BaseModel):
    id: int
    profile_id: int
    project_name: str
    start_time: date
    end_time: Optional[date] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tag_ids: List[int] = []
    tag_names: List[str] = []
    created_at: datetime
    updated_at: datetime


# ----- 档案完整响应 -----
class ProfileFullResponse(BaseModel):
    user_id: int
    ehr_no: str
    name: str
    group_name: Optional[str] = None
    base: Optional[ProfileBaseResponse] = None
    political: List[PoliticalInfoResponse] = []
    education: List[EducationInfoResponse] = []
    family: List[FamilyInfoResponse] = []
    resume: List[ResumeInfoResponse] = []
    reward: List[RewardInfoResponse] = []
    qualification: List[QualificationInfoResponse] = []
    achievement: List[AchievementInfoResponse] = []
    language: List[LanguageInfoResponse] = []
    contact: Optional[ContactInfoResponse] = None
    skill_tags: List[ProfileSkillTagResponse] = []
    development_intent: Optional[DevelopmentIntentResponse] = None
    project_summaries: List[ProjectSummaryResponse] = []
