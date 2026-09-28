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
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.crud.crud_ledger import ledger
from app.crud.crud_template import template
from app.portrait import models as portrait_models
from app.schemas.ledger import LedgerCreate
from app.schemas.template import TemplateCreate
from app.utils.logger import log_info


# 专用模板的固定标识 (全局唯一)
SPECIAL_WORK_TEMPLATE_NAME = "数字画像-专项工作"
SPECIAL_WORK_TEMPLATE_DEPT = "数字画像"


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
    return new_ledger