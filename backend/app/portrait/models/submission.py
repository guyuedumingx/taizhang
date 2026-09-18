"""
portrait 动态表单提交 + 审批节点

集成指南 §3 阶段 3 + PRD §9.1: portrait 3 类动态表单提交走审批流
  - 专项工作  (special_work)   PRD §6.1, 审批人下拉指定
  - 档案修改 (profile_edit)   PRD §12.1, 管理员审批
  - 亮点修改 (skill_tag_edit) PRD §12.2, 管理员审批 (高敏感必走)

家访单独走 portrait_home_visit_records (已建), 走独立 Workflow 实例,
与本 submission 表解耦, 由家访服务自行绑定 workflow_instance_id.

注意: PRD §6.2 活动报名 (B2) 不走审批, 走单独的 portrait_activity_signups 表,
       不在本 submission 表范围 (本批次不建活动报名相关表).

所有提交复用 taizhang Workflow 引擎:
  - SubmissionRecord.workflow_instance_id -> taizhang workflow_instances.id
  - ApprovalStatus 直接复用 taizhang ApprovalStatus 枚举 (集成指南 §5 雷区 6)

表名: portrait_ 前缀, 不动 taizhang 任何表
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class SubmissionRecord(Base):
    """动态表单提交记录 (3 类审批的载体)

    submission_type 区分:
      - special_work  : 专项工作 (PRD §6.1, 审批人下拉指定)
      - profile_edit  : 档案字段修改 (PRD §12.1, 管理员审批)
      - skill_tag_edit: 亮点标签修改 (PRD §12.2, 管理员审批, 高敏感必走)

    workflow_instance_id 关联 taizhang workflow_instances (审批流)
    """
    __tablename__ = "portrait_submission_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 3 类业务标识
    submission_type = Column(String(50), nullable=False, index=True)

    # 提交人 (FK -> taizhang users.id, 不反向)
    submitter_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 审批人快照 (冗余, 即使将来换审批人也能追溯)
    submitter_name = Column(String(100), nullable=False)
    submitter_ehr_id = Column(String(7), nullable=False)

    # 审批流绑定
    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=True, index=True)
    current_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 状态: pending / approved / rejected / cancelled / draft
    # 这里用 String 而不是导入 taizhang ApprovalStatus 枚举 (避免跨模块耦合)
    status = Column(String(20), default="pending", nullable=False, index=True)

    # 业务数据 (JSON 字符串, 各 type 自定义字段)
    #   special_work  : project_name, start_time, end_time, content, hours, skill_tags
    #   profile_edit  : field_name, old_value, new_value
    #   skill_tag_edit: tag_name, action (add/delete), sensitivity (normal/sensitive)
    payload = Column(Text, nullable=False)

    # 时间
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    # 关系: 不定义到 WorkflowInstance 的 relationship, 避免跨模块耦合


class ApprovalRecord(Base):
    """审批节点操作记录 (每次审批/驳回/转交留痕)

    不同于 taizhang WorkflowInstanceNode.approver_actions (JSON),
    本表做更详细的审计: 每条操作一行, 便于合规审计
    """
    __tablename__ = "portrait_approval_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("portrait_submission_records.id", ondelete="CASCADE"), nullable=False, index=True)

    # 操作人 (FK -> users.id)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 动作: approve / reject / transfer / withdraw
    action = Column(String(20), nullable=False)

    # 意见 (驳回/转交时必填, 通过时可空)
    comment = Column(Text, nullable=True)

    # 转交: 转给谁 (nullable, 仅 transfer 时非空)
    transferred_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=beijing_now)