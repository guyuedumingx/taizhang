"""
portrait schema 集中导出

集成指南 §3 阶段 4: portrait P4 后端 API MVP
"""
from app.portrait.schemas.common import ErrorResponse, PaginatedResponse
from app.portrait.schemas.profile import (
    AchievementInfo,
    AchievementInfoCreate,
    AchievementInfoUpdate,
    ContactInfo,
    ContactInfoCreate,
    ContactInfoUpdate,
    # P0.2: A4 兴趣 + A5 获奖
    InterestInfo,
    InterestInfoCreate,
    InterestInfoUpdate,
    AwardInfo,
    AwardInfoCreate,
    AwardInfoUpdate,
    # P0.7: B2 活动申报落子表
    ActivityRecord,
    EducationInfo,
    EducationInfoCreate,
    EducationInfoUpdate,
    EmergencyStaffUpdate,
    FamilyInfo,
    FamilyInfoCreate,
    FamilyInfoUpdate,
    LanguageInfo,
    LanguageInfoCreate,
    LanguageInfoUpdate,
    PoliticalInfo,
    PoliticalInfoCreate,
    PoliticalInfoUpdate,
    Profile,
    ProfileCreate,
    ProfileFull,
    ProfileListQuery,
    ProfileUpdate,
    QualificationInfo,
    QualificationInfoCreate,
    QualificationInfoUpdate,
    ResumeInfo,
    ResumeInfoCreate,
    ResumeInfoUpdate,
    RewardInfo,
    RewardInfoCreate,
    RewardInfoUpdate,

)
from app.portrait.schemas.submission import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalRecord,
    ApprovalRecordCreate,
    MySubmissionsQuery,
    Submission,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionUpdate,
)
from app.portrait.schemas.home_visit import (
    HomeVisit,
    HomeVisitApproveRequest,
    HomeVisitCreate,
    HomeVisitImportRow,
    HomeVisitImportSummary,
    HomeVisitListItem,
    HomeVisitListResponse,
    HomeVisitMatrix,
    HomeVisitMatrixCell,
    HomeVisitMatrixRow,
    HomeVisitRejectRequest,
    HomeVisitSubmitRequest,
    HomeVisitUpdate,
)
from app.portrait.schemas.training import (
    TrainingImportRow,
    TrainingImportSummary,
    TrainingRecord,
    TrainingRecordCreate,
    TrainingRecordUpdate,
)
from app.portrait.schemas.entry_exit import (
    EntryExitCreate,
    EntryExitImportRow,
    EntryExitImportSummary,
    EntryExitListResponse,
    EntryExitRecord,
    EntryExitStatistics,
    EntryExitUpdate,
)
from app.portrait.schemas.drill import (
    DrillCreate,
    DrillDetail,
    DrillImportRow,
    DrillImportSummary,
    DrillMatrix,
    DrillRecord,
    DrillUpdate,
)
# Week 3 P0.5: G7 组员调换历史 (只读 + 可删除, 无 Create/Update)
from app.portrait.schemas.group_transfer import (
    GroupTransferBase,
    GroupTransferListResponse,
    GroupTransferRecord,
)


__all__ = [
    # common
    "PaginatedResponse",
    "ErrorResponse",
    # profile
    "Profile",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileFull",
    "ProfileListQuery",
    "PoliticalInfo",
    "PoliticalInfoCreate",
    "PoliticalInfoUpdate",
    "EducationInfo",
    "EducationInfoCreate",
    "EducationInfoUpdate",
    "EmergencyStaffUpdate",
    "FamilyInfo",
    "FamilyInfoCreate",
    "FamilyInfoUpdate",
    "ResumeInfo",
    "ResumeInfoCreate",
    "ResumeInfoUpdate",
    "RewardInfo",
    "RewardInfoCreate",
    "RewardInfoUpdate",
    "QualificationInfo",
    "QualificationInfoCreate",
    "QualificationInfoUpdate",
    "AchievementInfo",
    "AchievementInfoCreate",
    "AchievementInfoUpdate",
    "LanguageInfo",
    "LanguageInfoCreate",
    "LanguageInfoUpdate",
    "ContactInfo",
    "ContactInfoCreate",
    "ContactInfoUpdate",
    # A3 技能标签 (Week 2 P0.5)



    # P0.2: A4 兴趣 + A5 获奖
    "InterestInfo",
    "InterestInfoCreate",
    "InterestInfoUpdate",
    "AwardInfo",
    "AwardInfoCreate",
    "AwardInfoUpdate",
    # P0.7: B2 活动申报落子表
    "ActivityRecord",
    # submission
    "Submission",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionDetail",
    "ApprovalRecord",
    "ApprovalRecordCreate",
    "ApprovalActionRequest",
    "ApprovalActionResponse",
    "MySubmissionsQuery",
    # home_visit (P6)
    "HomeVisit",
    "HomeVisitCreate",
    "HomeVisitUpdate",
    "HomeVisitSubmitRequest",
    "HomeVisitApproveRequest",
    "HomeVisitRejectRequest",
    "HomeVisitListItem",
    "HomeVisitListResponse",
    # training (PRD §10.3 占位)
    "TrainingRecord",
    "TrainingRecordCreate",
    "TrainingRecordUpdate",
    "TrainingImportRow",
    "TrainingImportSummary",
    # entry_exit (PRD §10.1 F5-F9)
    "EntryExitRecord",
    "EntryExitCreate",
    "EntryExitUpdate",
    "EntryExitListResponse",
    "EntryExitStatistics",
    "EntryExitImportRow",
    "EntryExitImportSummary",
    # drill (PRD §10.2 F2-F4)
    "DrillRecord",
    "DrillCreate",
    "DrillUpdate",
    "DrillDetail",
    "DrillMatrix",
    "DrillImportRow",
    "DrillImportSummary",
    # Week 3 P0.5: G7 组员调换历史 (PRD §11.4)
    "GroupTransferBase",
    "GroupTransferRecord",
    "GroupTransferListResponse",
]