"""工作流完成/驳回回调注册表 (重构方案 Phase 2)

此前引擎 approve/reject 完成时**内联写死**台账业务回写
(``ledger.approval_status = "approved"; ledger.status = "completed"``),
任何非台账业务复用引擎都会误改台账状态 —— 这是画像当年绕道自建状态机的
直接原因之一。

现在改为注册式: 按 subject_type 注册回调, 引擎只负责推进节点、在终态调用
``run_completion_hooks`` / ``run_rejection_hooks``。台账回调在本模块注册
(行为与原先逐字一致); 画像回调在画像侧模块注册
(app/portrait/services/workflow_bridge.py), 依赖方向保持 业务 → 引擎 单向。
"""
import logging
from typing import Callable, Dict

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger("taizhang.workflow")

CompletionHook = Callable[[Session, "models.WorkflowInstance"], None]
RejectionHook = Callable[[Session, "models.WorkflowInstance"], None]

_completion_hooks: Dict[str, CompletionHook] = {}
_rejection_hooks: Dict[str, RejectionHook] = {}


def register_completion_hook(subject_type: str, fn: CompletionHook) -> None:
    _completion_hooks[subject_type] = fn


def register_rejection_hook(subject_type: str, fn: RejectionHook) -> None:
    _rejection_hooks[subject_type] = fn


def run_completion_hooks(db: Session, instance: "models.WorkflowInstance") -> None:
    fn = _completion_hooks.get(instance.subject_type)
    if fn is None:
        return
    try:
        fn(db, instance)
    except Exception:
        # 回调失败不能吞 —— 但也不能让引擎静默半完成: 记日志后重抛,
        # 由调用方决定事务处置 (与原先内联回写的失败语义一致)
        logger.exception(
            "工作流完成回调失败 subject_type=%s instance_id=%s",
            instance.subject_type, instance.id,
        )
        raise


def run_rejection_hooks(db: Session, instance: "models.WorkflowInstance") -> None:
    fn = _rejection_hooks.get(instance.subject_type)
    if fn is None:
        return
    try:
        fn(db, instance)
    except Exception:
        logger.exception(
            "工作流驳回回调失败 subject_type=%s instance_id=%s",
            instance.subject_type, instance.id,
        )
        raise


# ---------------------------------------------------------------- 台账回调
def _ledger_completed(db: Session, instance: models.WorkflowInstance) -> None:
    """台账工作流完成 —— 与原先 approve_workflow_node 内联回写逐字一致"""
    ledger = db.query(models.Ledger).filter(models.Ledger.id == instance.ledger_id).first()
    if ledger:
        from datetime import datetime
        ledger.approval_status = "approved"
        ledger.approved_at = datetime.now()
        ledger.status = "completed"
        db.add(ledger)
        db.commit()


def _ledger_rejected(db: Session, instance: models.WorkflowInstance) -> None:
    """台账工作流驳回 —— 与原先 reject_workflow_node 内联回写逐字一致"""
    ledger = db.query(models.Ledger).filter(models.Ledger.id == instance.ledger_id).first()
    if ledger:
        ledger.approval_status = "rejected"
        ledger.status = "returned"
        db.add(ledger)
        db.commit()


register_completion_hook("ledger", _ledger_completed)
register_rejection_hook("ledger", _ledger_rejected)
