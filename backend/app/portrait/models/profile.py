"""
portrait 档案主表 + 10 个子表

集成指南 §3 阶段 2.2: 把 digital_portrait 档案域 (Profile + 12 子表) 搬到台账
台账原表 0 改动, portrait 表用独立 schema

User 表不复用 (taizhang 已有), Profile.user_id 指向 taizhang users.id
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class Profile(Base):
    """数字画像主档案 - 1:1 关联 taizhang users"""
    __tablename__ = "portrait_profiles"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    gender = Column(String(10), nullable=True)
    nation = Column(String(50), nullable=True)
    birth_date = Column(Date, nullable=True)
    job_title = Column(String(200), nullable=True)
    id_type = Column(String(50), nullable=True)
    # P0.1 隐私裁剪: 移除 id_number / native_place / birth_place / household_place
    work_start_date = Column(Date, nullable=True)
    hire_date = Column(Date, nullable=True)
    marital_status = Column(String(20), nullable=True)
    is_emergency_staff = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    political = relationship("PoliticalInfo", back_populates="profile", order_by="PoliticalInfo.join_date")
    education = relationship("EducationInfo", back_populates="profile")
    family = relationship("FamilyInfo", back_populates="profile")
    resume = relationship("ResumeInfo", back_populates="profile", order_by="ResumeInfo.start_time")
    reward = relationship("RewardInfo", back_populates="profile", order_by="RewardInfo.reward_time")
    qualification = relationship("QualificationInfo", back_populates="profile", order_by="QualificationInfo.obtain_time")
    achievement = relationship("AchievementInfo", back_populates="profile", order_by="AchievementInfo.obtain_time")
    language = relationship("LanguageInfo", back_populates="profile")
    # P0.2 新增: A4 兴趣 + A5 获奖
    interests = relationship("InterestInfo", back_populates="profile", order_by="InterestInfo.created_at")
    awards = relationship("AwardInfo", back_populates="profile", order_by="AwardInfo.award_time.desc()")
    # P0.7: B2 活动申报通过后落入
    activities = relationship("ActivityRecord", back_populates="profile", order_by="ActivityRecord.activity_time.desc()")
    contact = relationship("ContactInfo", back_populates="profile", uselist=False)
    skill_tags = relationship("ProfileSkillTag", back_populates="profile")
    development_intent = relationship("DevelopmentIntent", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    project_summaries = relationship("ProjectSummary", back_populates="profile", cascade="all, delete-orphan")


class PoliticalInfo(Base):
    __tablename__ = "portrait_political_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    political_status = Column(String(50), nullable=True)
    join_date = Column(Date, nullable=True)
    introducer = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="political")


class EducationInfo(Base):
    __tablename__ = "portrait_education_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    education_category = Column(String(50), nullable=True)
    education_type = Column(String(50), nullable=True)
    education_level = Column(String(50), nullable=True)
    degree = Column(String(50), nullable=True)
    school = Column(String(200), nullable=True)
    major_name = Column(String(200), nullable=True)
    duration_years = Column(String(20), nullable=True)
    enrollment_date = Column(Date, nullable=True)
    graduation_date = Column(Date, nullable=True)
    completion_status = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="education")


class FamilyInfo(Base):
    __tablename__ = "portrait_family_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    name = Column(String(100), nullable=True)
    gender = Column(String(10), nullable=True)
    relation = Column(String(50), nullable=True)
    birth_date = Column(Date, nullable=True)
    work_unit_and_title = Column(String(500), nullable=True)
    political_status = Column(String(50), nullable=True)
    employment_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="family")


class ResumeInfo(Base):
    __tablename__ = "portrait_resume_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    start_time = Column(Date, nullable=True)
    end_time = Column(Date, nullable=True)
    unit_and_title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="resume")


class RewardInfo(Base):
    __tablename__ = "portrait_reward_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    reward_type = Column(String(20), nullable=True)
    reward_time = Column(Date, nullable=True)
    reward_name = Column(String(300), nullable=True)
    reward_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="reward")


class QualificationInfo(Base):
    __tablename__ = "portrait_qualification_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    qualification_name = Column(String(200), nullable=True)
    obtain_time = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="qualification")


class AchievementInfo(Base):
    __tablename__ = "portrait_achievement_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    achievement_name = Column(String(300), nullable=True)
    obtain_time = Column(Date, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="achievement")


class LanguageInfo(Base):
    __tablename__ = "portrait_language_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    language = Column(String(50), nullable=True)
    proficiency = Column(String(50), nullable=True)
    cert_level_or_score = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="language")


class ContactInfo(Base):
    __tablename__ = "portrait_contact_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), unique=True, nullable=False)
    # P0.1 隐私裁剪: 移除 mobile / office_phone / home_phone / home_address
    email = Column(String(100), nullable=True)
    commute_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="contact")


# ============================================================================
# P0.2 新增: A4 兴趣爱好 (PRD §5.4) + A5 获奖信息 (PRD §5.5)
# ============================================================================
class InterestInfo(Base):
    """兴趣爱好子表 (1:N, 与技能标签分离) - PRD §5.4"""
    __tablename__ = "portrait_interest_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    interest_name = Column(String(100), nullable=False)
    # 熟练度枚举: 入门/熟练/精通 (Pydantic 层校验)
    proficiency = Column(String(20), nullable=False, default="入门")
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="interests")


class AwardInfo(Base):
    """获奖信息子表 (1:N, 按获奖时间倒序) - PRD §5.5"""
    __tablename__ = "portrait_award_info"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    award_name = Column(String(200), nullable=False)
    awarding_organization = Column(String(200), nullable=True)
    award_time = Column(Date, nullable=True)
    # 级别枚举: 国家级/省部级/行级 (Pydantic 层校验)
    level = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="awards")


# ============================================================================
# P0.7: B2 活动申报审批通过后落子表 (PRD §6.2)
# ============================================================================
class ActivityRecord(Base):
    """活动记录子表 (1:N, 按活动时间倒序) - PRD §6.2 v2.1

    审批通过 activity_claim submission 后, 由 approve_submission 钩子创建
    字段对齐 B2 表单必填+选填
    """
    __tablename__ = "portrait_activity_record"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    activity_name = Column(String(200), nullable=False)
    activity_time = Column(Date, nullable=False)
    # 类型枚举: 运动会/文艺/志愿/培训/其他
    activity_type = Column(String(20), nullable=False)
    organizer = Column(String(200), nullable=False)
    # 选填: 获奖或参与情况
    award_or_participation = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    hours = Column(Integer, nullable=True)
    # 审批来源 (B2 submission_id), 留痕
    source_submission_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="activities")