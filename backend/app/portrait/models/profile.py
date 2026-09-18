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
    id_number = Column(String(50), nullable=True)
    native_place = Column(String(200), nullable=True)
    birth_place = Column(String(200), nullable=True)
    household_place = Column(String(200), nullable=True)
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
    mobile = Column(String(20), nullable=True)
    office_phone = Column(String(20), nullable=True)
    home_phone = Column(String(20), nullable=True)
    home_address = Column(String(500), nullable=True)
    email = Column(String(100), nullable=True)
    commute_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    profile = relationship("Profile", back_populates="contact")