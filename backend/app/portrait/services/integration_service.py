"""
portrait 与台账系统的联动 service (P8)

设计目标: special_work 审批通过后, 自动在台账系统创建对应的 ledger 实例.

集成指南 §5 雷区 3 合规:
  - 不混入台账业务字段, 用 ledger.data 顶层 __portrait_source__ 标记来源
集成指南 §5 雷区 4 合规:
  - portrait + ledger 同 schema (台账库); 联动在 submission approve commit 之后
  - 联动失败必须显性化抛 500 (Rule 12: 失败必须显性化)
集成指南 §5 雷区 7 合规:
  - 走 service 层调用, 不绕过任何依赖
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.crud.crud_ledger import ledger
from app.crud.crud_template import template
from app.models.workflow import ApprovalStatus
from app.portrait import models as portrait_models
from app.schemas.ledger import LedgerCreate
from app.schemas.template import TemplateCreate
from app.utils.logger import log_info


# 专用模板的固定标识 (全局唯一)
SPECIAL_WORK_TEMPLATE_NAME = "数字画像-专项工作"
SPECIAL_WORK_TEMPLATE_DEPT = "数字画像"
# 专用 workflow 的固定标识 (阶段 F: Workflow 真绑)
# 注意: 必须 ≥2 节点, 否则 crud.workflow_instance.create_with_nodes line 68 的
# `instance_nodes[1].id` 会 IndexError (隐藏假设: 至少 1 个开始 + 1 个审批)
SPECIAL_WORK_WORKFLOW_NAME = "数字画像-专项工作流程"


def _find_or_create_special_work_template(
    db: Session, *, creator: models.User
) -> models.Template:
    """查找或创建"数字画像-专项工作"专用 template

    第一次联动时自动建模板, 后续直接复用 (P5 阶段模板表已有 name 字段 index).
    """
    tmpl = db.query(models.Template).filter(
        models.Template.name == SPECIAL_WORK_TEMPLATE_NAME
    ).first()
    if tmpl:
        return tmpl
    tmpl_in = TemplateCreate(
        name=SPECIAL_WORK_TEMPLATE_NAME,
        description="由 portrait special_work 审批通过自动生成的台账模板 (P8)",
        department=SPECIAL_WORK_TEMPLATE_DEPT,
        is_system=True,
        default_metadata={
            "__auto_created__": True,
            "__source__": "portrait_special_work",
        },
        fields=[],  # 不预设字段, payload 直接进 ledger.data
    )
    new_tmpl = template.create(db, obj_in=tmpl_in, creator_id=creator.id)
    log_info(
        module="portrait",
        action="integration.template_auto_create",
        message=f"自动创建 special_work 联动模板 #{new_tmpl.id}",
        user_id=creator.id,
        resource_type="template",
        resource_id=str(new_tmpl.id),
    )
    return new_tmpl


def _find_or_create_special_work_workflow(
    db: Session, *, creator: models.User
) -> models.Workflow:
    """查找或创建"数字画像-专项工作"专用 workflow (阶段 F)

    形状: 2 节点 (开始 + 终审). ≥2 节点是硬约束 — 看 crud_workflow_instance.create_with_nodes
    line 68 (`instance_nodes[1].id`). 违反就 IndexError, 这是现有 bug, 这里仅规避.
    phase F 词面语义是"submission 写入 workflow_instance_id", 不要求真实跑审批流,
    所以节点定义仅满足"能建出 workflow_instance"即可, 不预设审批人 (后续阶段再扩展).

    第一次联动时自动建 workflow + nodes, 后续直接复用 (P8 + F 模式同 template).
    """
    existing = db.query(models.Workflow).filter(
        models.Workflow.name == SPECIAL_WORK_WORKFLOW_NAME
    ).first()
    if existing:
        # 节点可能为空 (e.g. 历史脏数据), 缺失时补齐 2 节点兜底
        node_rows = (
            db.query(models.WorkflowNode)
            .filter(models.WorkflowNode.workflow_id == existing.id)
            .order_by(models.WorkflowNode.order_index)
            .all()
        )
        if not node_rows:
            _add_special_work_nodes(db, workflow_id=existing.id)
        return existing

    new_wf = models.Workflow(
        name=SPECIAL_WORK_WORKFLOW_NAME,
        description="由 portrait special_work 审批通过自动生成的工作流 (P8+阶段F)",
        is_active=True,
        created_by=creator.id,
    )
    db.add(new_wf)
    db.flush()  # 获取 id
    _add_special_work_nodes(db, workflow_id=new_wf.id)

    # 注: log_info 用独立 SessionLocal, 在 SQLite 上与未 commit 的事务并发写 system_logs
    # 会触发 'database is locked'. 由 caller (sync_special_work_to_ledger) 整体打日志更稳.
    return new_wf


def _add_special_work_nodes(db: Session, *, workflow_id: int) -> None:
    """补建 workflow 的 2 节点 (开始 + 终审). 仅内部 helper, 不暴露给外部."""
    start_node = models.WorkflowNode(
        workflow_id=workflow_id,
        name="开始",
        description="special_work 联动进入点 (自动)",
        node_type="start",
        order_index=1,
        is_final=False,
        multi_approve_type="any",
    )
    end_node = models.WorkflowNode(
        workflow_id=workflow_id,
        name="终审",
        description="special_work 联动终审节点 (审批时已过, 自动置为 approved)",
        node_type="approval",
        order_index=2,
        is_final=True,
        multi_approve_type="any",
    )
    db.add(start_node)
    db.add(end_node)
    db.flush()


def sync_special_work_to_ledger(
    db: Session, *, submission: portrait_models.SubmissionRecord
) -> Optional[models.Ledger]:
    """special_work 审批通过后, 在台账系统创建对应 ledger

    Args:
        db: DB session
        submission: 已审批通过的 special_work submission (status='approved')

    Returns:
        新创建的 Ledger 对象; 非 special_work 类型直接返回 None (上层调用方决定是否触发)

    Raises:
        HTTPException 500: 联动失败时显性化抛出 (Rule 12)
    """
    # 1) 仅 special_work 触发联动
    if submission.submission_type != "special_work":
        return None

    # 2) 幂等: 已联动过则跳过 (P8 防重复, 防御性)
    if submission.synced_ledger_id is not None:
        log_info(
            module="portrait",
            action="integration.skip_already_synced",
            message=f"special_work #{submission.id} 已联动到 ledger #{submission.synced_ledger_id}, 跳过",
            user_id=submission.submitter_user_id,
            resource_type="submission",
            resource_id=str(submission.id),
        )
        return None

    # 3) 解析 payload (DB 存的是 JSON 字符串)
    raw = submission.payload
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"联动失败: submission #{submission.id} payload 不是合法 JSON: {exc}"
                )
            ) from exc
    else:
        payload = raw or {}

    # 4) 找提交人
    submitter = (
        db.query(models.User)
        .filter(models.User.id == submission.submitter_user_id)
        .first()
    )
    if not submitter:
        raise HTTPException(
            status_code=500,
            detail=(
                f"联动失败: submission #{submission.id} 提交人 user_id="
                f"{submission.submitter_user_id} 不存在"
            )
        )

    # 5) 找/建模板
    tmpl = _find_or_create_special_work_template(db, creator=submitter)

    # 6) 组装 ledger.data (payload 字段 + portrait_source 元数据)
    # 雷区 3 合规: 用 __portrait_source__ 命名空间标记来源, 不混入台账字段
    ledger_data = {
        **payload,
        "__portrait_source__": {
            "submission_id": submission.id,
            "submission_type": submission.submission_type,
            "submitter_user_id": submission.submitter_user_id,
            "submitter_ehr_id": submission.submitter_ehr_id,
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at
                else None
            ),
        },
    }

    # 7) 创建 ledger
    name = payload.get("project_name") or f"special_work #{submission.id}"
    content = payload.get("content") or ""
    description = content[:500]  # 截断, 防止 Rule 8 限制

    ledger_in = LedgerCreate(
        name=name,
        description=description,
        template_id=tmpl.id,
        team_id=submitter.team_id,  # 提交人所在组
        data=ledger_data,
        status="active",
        approval_status="approved",  # portrait 已审批通过, 台账直接 approved
    )
    new_ledger = ledger.create(
        db,
        obj_in=ledger_in,
        created_by_id=submitter.id,
        updated_by_id=submitter.id,
    )

    # 8) 写回 submission.synced_ledger_id (本方法返回后由 caller commit)
    submission.synced_ledger_id = new_ledger.id

    log_info(
        module="portrait",
        action="integration.sync_special_work",
        message=f"special_work #{submission.id} 已同步到 ledger #{new_ledger.id}",
        user_id=submitter.id,
        resource_type="ledger",
        resource_id=str(new_ledger.id),
    )

    # 9) 阶段 F: 联动 WorkflowInstance, 回填 submission.workflow_instance_id
    # 业务现状: ledger_id NOT NULL+UNIQUE (models/workflow.py line 84), 必须先有 ledger.
    # 因此 submission 创建时无法绑 (那时还没 ledger); 在审批通过 + 建 ledger 之后建.
    # 状态语义: special_work 已审批通过 → workflow_instance 直接 completed
    # (不走流程审批, 仅作为与台账 ledger 的 1:1 壳, 满足"真绑"语义要求).
    # 关于为何手写而非用 crud_workflow_instance.create_with_nodes:
    #   - 该 helper 假设 workflow ≥2 节点 (line 68 instance_nodes[1].id),
    #     单节点工作流会 IndexError. 我们这里有 2 节点, 可绕过; 但 helper 内部
    #     还硬编码 db.commit(), 与 caller 的统一 commit 冲突, 易引入事务分叉.
    #   - 阶段 F 词面要求仅"submission 写入 workflow_instance_id", 不强求运行审批流,
    #     手写最简实现 + 单 commit 更安全.
    try:
        wf = _find_or_create_special_work_workflow(db, creator=submitter)
        new_wf_inst = models.WorkflowInstance(
            workflow_id=wf.id,
            ledger_id=new_ledger.id,
            created_by=submitter.id,
            status="completed",  # special_work 审批已通过 → 直接 completed
            completed_at=datetime.now(),
            current_node_id=None,
        )
        db.add(new_wf_inst)
        db.flush()

        # 把 workflow 的所有节点对应建 instance_nodes (instance 视角已全部 approved)
        wf_nodes = (
            db.query(models.WorkflowNode)
            .filter(models.WorkflowNode.workflow_id == wf.id)
            .order_by(models.WorkflowNode.order_index)
            .all()
        )
        for wfn in wf_nodes:
            db_inst_node = models.WorkflowInstanceNode(
                workflow_instance_id=new_wf_inst.id,
                workflow_node_id=wfn.id,
                status=ApprovalStatus.APPROVED,
                approver_id=submitter.id,
                completed_at=datetime.now(),
            )
            db.add(db_inst_node)

        # 10) 回填 submission.workflow_instance_id (本方法返回后由 caller commit)
        submission.workflow_instance_id = new_wf_inst.id

        # 注: log_info 用独立 SessionLocal, 在 SQLite 上与未 commit 的事务并发写 system_logs
        # 会触发 'database is locked'. 由 caller (submission_service.approve) 统一打日志更稳.
    except HTTPException:
        raise  # 上面已显性化, 透传
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"联动失败: special_work #{submission.id} 创建 workflow_instance "
                f"时未预期异常: {exc}"
            ),
        ) from exc

    return new_ledger