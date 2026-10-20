"""画像 ↔ 台账 Workflow 引擎桥接层 (重构方案 Phase 2 Layer 2)

此前画像自建两套审批状态机 (submission_service / home_visit_service),
根因是 WorkflowInstance.ledger_id NOT NULL+UNIQUE 把引擎焊死在台账上
(Phase 2 Layer 1 已泛化为 subject_type+subject_id)。本模块把画像接回引擎:

  - 提交/家访提交时创建**真实**实例 (审批人直落 approval 节点);
  - 通过/驳回/撤回委托引擎 crud 推进, 画像行只保留"读模型镜像"
    (status / current_approver_id / completed_at, 画像列表与前端读这里);
  - 镜像同步函数同时注册为引擎回调 (workflow_hooks), 即使有人从台账的
    通用审批端点操作画像实例, 镜像也不会漂移;
  - 模板按名 find-or-create, 新环境不依赖 init_portrait_workflows 的执行
    顺序 (部署友好; 该脚本播种的同名模板会被直接复用)。

依赖方向: portrait → 引擎 (单向)。引擎对本模块一无所知。
"""
import logging
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app import crud, models
from app.portrait import models as portrait_models
from app.services.workflow_hooks import (
    register_completion_hook,
    register_rejection_hook,
)

logger = logging.getLogger("taizhang.portrait")

SUBJECT_SUBMISSION = "portrait_submission"
SUBJECT_HOME_VISIT = "portrait_home_visit"

# submission_type -> 审批模板名 (与 init_portrait_workflows.py 播种的同名复用)
SUBMISSION_WORKFLOW_NAMES = {
    "special_work": "portrait_special_work",
    "profile_edit": "portrait_profile_edit",
    "activity_claim": "portrait_activity_claim",
}
HOME_VISIT_WORKFLOW_NAME = "portrait_home_visit"


# ---------------------------------------------------------------- 模板
def _ensure_template(db: Session, name: str, description: str) -> models.Workflow:
    """find-or-create 三节点审批模板 (提交/审批/完成)。

    审批节点不挂角色/名单 —— 画像的语义是"提交时指定审批人", 审批人落在
    实例节点上 (见 crud create_for_subject 的 approval_node_approver_id)。
    """
    wf = db.query(models.Workflow).filter(models.Workflow.name == name).first()
    if wf:
        return wf
    wf = models.Workflow(name=name, description=description, is_active=True, created_by=1)
    db.add(wf)
    db.flush()
    for node_name, node_type, order_index, is_final in [
        ("提交", "start", 1, False),
        ("审批", "approval", 2, False),
        ("完成", "end", 3, True),
    ]:
        db.add(models.WorkflowNode(
            workflow_id=wf.id,
            name=node_name,
            node_type=node_type,
            order_index=order_index,
            is_final=is_final,
            multi_approve_type="any",
        ))
    db.commit()
    logger.info("自动创建画像审批模板: %s (id=%s)", name, wf.id)
    return wf


# ---------------------------------------------------------------- 实例生命周期
def start_submission_workflow(
    db: Session,
    *,
    submission: portrait_models.SubmissionRecord,
    approver_id: int,
) -> models.WorkflowInstance:
    template_name = SUBMISSION_WORKFLOW_NAMES.get(submission.submission_type)
    if template_name is None:
        raise ValueError(f"submission_type {submission.submission_type} 无对应审批模板")
    wf = _ensure_template(db, template_name, f"数字画像·{submission.submission_type} 审批")
    instance = crud.workflow_instance.create_for_subject(
        db,
        workflow_id=wf.id,
        created_by=submission.submitter_user_id,
        subject_type=SUBJECT_SUBMISSION,
        subject_id=submission.id,
        approval_node_approver_id=approver_id,
    )
    submission.workflow_instance_id = instance.id
    db.commit()
    return instance


def start_home_visit_workflow(
    db: Session,
    *,
    record: "portrait_models.HomeVisitRecord",
    approver_id: int,
) -> models.WorkflowInstance:
    wf = _ensure_template(db, HOME_VISIT_WORKFLOW_NAME, "数字画像·家访审批")
    instance = crud.workflow_instance.create_for_subject(
        db,
        workflow_id=wf.id,
        created_by=record.visitor_user_id,
        subject_type=SUBJECT_HOME_VISIT,
        subject_id=record.id,
        approval_node_approver_id=approver_id,
    )
    record.workflow_instance_id = instance.id
    db.commit()
    return instance


def ensure_submission_instance(
    db: Session, submission: portrait_models.SubmissionRecord, *, approver_id: int
) -> models.WorkflowInstance:
    """兼容存量 pending 数据: 没有实例的旧提交在审批动作前补建。"""
    if submission.workflow_instance_id:
        instance = (
            db.query(models.WorkflowInstance)
            .filter(models.WorkflowInstance.id == submission.workflow_instance_id)
            .first()
        )
        if instance:
            return instance
    return start_submission_workflow(db, submission=submission, approver_id=approver_id)


def approve(
    db: Session, *, instance_id: int, user_id: int, comment: Optional[str] = None
) -> Tuple[Dict, models.WorkflowInstance]:
    """推进当前节点; 画像语义是单步审批, 完成即终态。

    注意这里走 crud 层 (不经过 workflow_instance_service, 避免与画像自身的
    权限语义双重判定), 因此**必须**在此显式同步镜像 —— 引擎回调只在
    service 层路径触发, 本函数承担画像路径的镜像同步。
    """
    instance = (
        db.query(models.WorkflowInstance).filter(models.WorkflowInstance.id == instance_id).first()
    )
    if not instance:
        raise ValueError(f"工作流实例 {instance_id} 不存在")
    result = crud.workflow_instance.approve_current_node(
        db, instance_id=instance_id, user_id=user_id, comment=comment
    )
    if result.get("success") and result.get("workflow_completed"):
        _COMPLETION_SYNCS[instance.subject_type](db, instance)
    return result, instance


def reject(
    db: Session, *, instance_id: int, user_id: int, comment: str
) -> Tuple[Dict, models.WorkflowInstance]:
    instance = (
        db.query(models.WorkflowInstance).filter(models.WorkflowInstance.id == instance_id).first()
    )
    if not instance:
        raise ValueError(f"工作流实例 {instance_id} 不存在")
    result = crud.workflow_instance.reject_current_node(
        db, instance_id=instance_id, user_id=user_id, comment=comment
    )
    if result.get("success") and result.get("workflow_rejected"):
        _REJECTION_SYNCS[instance.subject_type](db, instance)
    return result, instance


def cancel(db: Session, *, instance_id: int) -> None:
    crud.workflow_instance.cancel(db, instance_id=instance_id)


def reassign_approver(db: Session, *, instance_id: int, new_approver_id: int) -> None:
    """转交: 把当前 approval 节点的审批人改为新人 (镜像字段由调用方同步)。"""
    instance = (
        db.query(models.WorkflowInstance).filter(models.WorkflowInstance.id == instance_id).first()
    )
    if not instance or not instance.current_node_id:
        return
    node = (
        db.query(models.WorkflowInstanceNode)
        .filter(models.WorkflowInstanceNode.id == instance.current_node_id)
        .first()
    )
    if node:
        node.approver_id = new_approver_id
        db.commit()


# ---------------------------------------------------------------- 镜像同步 (也是引擎回调)
def _load_submission(db: Session, instance) -> Optional[portrait_models.SubmissionRecord]:
    return (
        db.query(portrait_models.SubmissionRecord)
        .filter(portrait_models.SubmissionRecord.id == instance.subject_id)
        .first()
    )


def sync_submission_completed(db: Session, instance) -> None:
    submission = _load_submission(db, instance)
    if submission is None or submission.status != "pending":
        return
    submission.status = "approved"
    submission.completed_at = _now()
    submission.current_approver_id = None
    db.commit()


def sync_submission_rejected(db: Session, instance) -> None:
    submission = _load_submission(db, instance)
    if submission is None or submission.status != "pending":
        return
    submission.status = "rejected"
    submission.completed_at = _now()
    submission.current_approver_id = None
    db.commit()


def sync_home_visit_completed(db: Session, instance) -> None:
    record = db.query(portrait_models.HomeVisitRecord).filter(
        portrait_models.HomeVisitRecord.id == instance.subject_id
    ).first()
    if record is None or record.status != "pending":
        return
    record.status = "approved"
    record.current_approver_id = None
    record.completed_at = _now()
    db.commit()


def sync_home_visit_rejected(db: Session, instance) -> None:
    record = db.query(portrait_models.HomeVisitRecord).filter(
        portrait_models.HomeVisitRecord.id == instance.subject_id
    ).first()
    if record is None or record.status != "pending":
        return
    record.status = "rejected"
    record.current_approver_id = None
    record.completed_at = _now()
    db.commit()


def _now():
    from datetime import datetime
    return datetime.now()


# 注册引擎回调: 画像实例被任意路径 (含台账通用审批端点) 终结时镜像保持一致。
# 决策 3 的业务联动 (项目总结/活动记录) 不放这里 —— 那是提单审批的专属语义,
# 由 submission_service.approve 在引擎推进后显式执行 (失败要 500 显性化)。
register_completion_hook(SUBJECT_SUBMISSION, sync_submission_completed)
register_rejection_hook(SUBJECT_SUBMISSION, sync_submission_rejected)
register_completion_hook(SUBJECT_HOME_VISIT, sync_home_visit_completed)
register_rejection_hook(SUBJECT_HOME_VISIT, sync_home_visit_rejected)

# 画像直连路径 (本模块 approve/reject 走 crud 层不触发引擎回调) 的镜像同步表
_COMPLETION_SYNCS = {SUBJECT_SUBMISSION: sync_submission_completed, SUBJECT_HOME_VISIT: sync_home_visit_completed}
_REJECTION_SYNCS = {SUBJECT_SUBMISSION: sync_submission_rejected, SUBJECT_HOME_VISIT: sync_home_visit_rejected}
