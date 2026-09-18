"""
数字画像 portrait/ 子目录模型注册

集成指南 §3 阶段 2.2: portrait 业务表全部进台账仓, 台账原模型 0 改动
台账 (taizhang) 的 models 完全不动, portrait 通过 import 此模块让 SQLAlchemy 知道
所有新增表(供 create_all() / 未来 Alembic 用)。

当前 (P2):
  - PortraitUserMetadata (扩展 taizhang User 的 portrait 字段)
  - Profile + 10 子表 (political/education/family/resume/reward/qualification/
    achievement/language/contact/skill_tags)
  - DevelopmentIntent, ProjectSummary, ProjectSummaryTag
  - SkillTagTemplate, ProfileSkillTag
  - OperationLog, HomeVisitRecord, GroupTransferHistory
"""
from app.portrait.models._base import PORTRAIT_SCHEMA, beijing_now
from app.portrait.models.intent_project import (
    DevelopmentIntent,
    ProfileSkillTag,
    ProjectSummary,
    ProjectSummaryTag,
    SkillTagTemplate,
)
from app.portrait.models.log_visit_transfer import (
    GroupTransferHistory,
    HomeVisitRecord,
    OperationLog,
)
from app.portrait.models.profile import (
    AchievementInfo,
    ContactInfo,
    EducationInfo,
    FamilyInfo,
    LanguageInfo,
    PoliticalInfo,
    Profile,
    QualificationInfo,
    ResumeInfo,
    RewardInfo,
)
from app.portrait.models.submission import ApprovalRecord, SubmissionRecord
from app.portrait.models.user_metadata import PortraitUserMetadata

__all__ = [
    "PORTRAIT_SCHEMA",
    "beijing_now",
    # user 扩展
    "PortraitUserMetadata",
    # 档案
    "Profile",
    "PoliticalInfo",
    "EducationInfo",
    "FamilyInfo",
    "ResumeInfo",
    "RewardInfo",
    "QualificationInfo",
    "AchievementInfo",
    "LanguageInfo",
    "ContactInfo",
    # 发展意向 + 项目
    "DevelopmentIntent",
    "ProjectSummary",
    "ProjectSummaryTag",
    # 技能标签
    "SkillTagTemplate",
    "ProfileSkillTag",
    # 提交 + 审批 (PRD §9.1)
    "SubmissionRecord",
    "ApprovalRecord",
    # 日志 + 家访 + 调组
    "OperationLog",
    "HomeVisitRecord",
    "GroupTransferHistory",
]