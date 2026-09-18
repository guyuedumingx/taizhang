"""
portrait 发展意向 + 项目总结 + 技能标签
"""
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class DevelopmentIntent(Base):
    """发展意向 - 1:1 关联 Profile"""
    __tablename__ = "portrait_development_intent"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)

    development_path = Column(String(50), nullable=True)
    short_term_goal = Column(Text, nullable=True)
    mid_term_goal = Column(Text, nullable=True)

    core_abilities = Column(Text, nullable=True)
    learning_methods = Column(Text, nullable=True)
    learning_courses = Column(Text, nullable=True)

    rotation_interest = Column(String(20), nullable=True)
    rotation_target = Column(String(200), nullable=True)
    project_interests = Column(Text, nullable=True)

    other_comments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    profile = relationship("Profile", back_populates="development_intent")


class ProjectSummary(Base):
    """项目总结"""
    __tablename__ = "portrait_project_summary"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(200), nullable=False)
    start_time = Column(Date, nullable=False)
    end_time = Column(Date, nullable=True)
    role = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    profile = relationship("Profile", back_populates="project_summaries")
    tags = relationship("ProjectSummaryTag", back_populates="project", cascade="all, delete-orphan")


class ProjectSummaryTag(Base):
    """项目-技能标签中间表"""
    __tablename__ = "portrait_project_summary_tags"
    __table_args__ = (
        UniqueConstraint("project_id", "tag_id", name="portrait_uq_project_tag"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("portrait_project_summary.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("portrait_skill_tag_templates.id", ondelete="CASCADE"), nullable=False)

    project = relationship("ProjectSummary", back_populates="tags")
    tag = relationship("SkillTagTemplate")


class SkillTagTemplate(Base):
    """预定义技能标签模板 (管理员维护)"""
    __tablename__ = "portrait_skill_tag_templates"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=beijing_now)


class ProfileSkillTag(Base):
    """用户档案-技能标签 N:M (支持预定义 + 自定义, template_id 为 NULL 表示自定义)"""
    __tablename__ = "portrait_profile_skill_tags"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("portrait_profiles.id"), nullable=False)
    tag_name = Column(String(100), nullable=False)
    template_id = Column(Integer, ForeignKey("portrait_skill_tag_templates.id"), nullable=True)
    created_at = Column(DateTime, default=beijing_now)

    profile = relationship("Profile", back_populates="skill_tags")