"""
B1 专项工作审批通过后落项目总结子表 (2026-10-16 决策 3)

设计目标: special_work 审批通过后, 落 portrait_project_summary (画像自有表),
**不再写台账 ledgers**。画像将来单独部署时台账表不存在, 旧链路会断。

落点字段对照 (决策 3 由业务方给定):
    用户名 -> profile_id (关联本人档案)
    时间   -> start_time + end_time
    专项名称 -> project_name
    专项内容 -> description
    完成情况 -> completion_status

沿用 activity_sync_service 的模式 (commit 后再同步, 失败抛 500 显性化 - Rule 12)
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.portrait import models as portrait_models


def sync_special_work_to_project_summary(
    db: Session, *, submission: portrait_models.SubmissionRecord
) -> Optional[portrait_models.ProjectSummary]:
    """B1 专项工作审批通过后, 落 portrait_project_summary

    步骤:
      1. 解析 submission.payload (JSON 字符串)
      2. 找 submitter 对应 Profile (没有则创建空档案)
      3. 落 ProjectSummary
      4. 返回新 record (caller commit)

    失败规则 (Rule 12):
      - payload JSON 损坏: 抛 500
      - 必填字段缺失: 抛 500 (校验在前, 理论上不会到这)
      - profile 创建失败: 抛 500
    """
    try:
        payload = json.loads(submission.payload) if submission.payload else {}
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"special_work payload 解析失败: {exc}",
        ) from exc

    # 必填字段 (validate 阶段已保证, 此处防御性)
    for f in ("project_name", "start_time"):
        if not payload.get(f):
            raise HTTPException(
                status_code=500,
                detail=f"special_work 落项目总结时缺少字段: {f}",
            )

    # 幂等: 同一 submission 只落一次 (批准旧的 synced_ledger_id 防重逻辑)
    existing = (
        db.query(portrait_models.ProjectSummary)
        .filter(portrait_models.ProjectSummary.source_submission_id == submission.id)
        .first()
    )
    if existing:
        return None

    # 找 submitter
    from app import models as app_models

    submitter_user = (
        db.query(app_models.User)
        .filter(app_models.User.id == submission.submitter_user_id)
        .first()
    )
    if not submitter_user:
        raise HTTPException(
            status_code=500,
            detail=(
                f"special_work 落项目总结: submitter "
                f"{submission.submitter_user_id} 不存在"
            ),
        )

    # 找/建 Profile
    profile = (
        db.query(portrait_models.Profile)
        .filter(portrait_models.Profile.user_id == submitter_user.id)
        .first()
    )
    if not profile:
        profile = portrait_models.Profile(user_id=submitter_user.id)
        db.add(profile)
        db.flush()

    summary = portrait_models.ProjectSummary(
        profile_id=profile.id,
        project_name=payload["project_name"],
        start_time=_to_date(payload["start_time"], "start_time"),
        end_time=_to_date(payload.get("end_time"), "end_time"),
        description=payload.get("content"),
        hours=payload.get("hours"),
        # 提交人填了完成情况就用填的, 没填默认"已完成" (审批通过即视为完成)
        completion_status=payload.get("completion_status") or "已完成",
        source_submission_id=submission.id,
    )
    db.add(summary)
    db.flush()
    db.refresh(summary)
    return summary


def _to_date(value, field_name: str):
    """payload 里的时间是 ISO 字符串, 转 date; 空值返回 None"""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        try:
            # 兼容带时分秒的 ISO 8601
            return datetime.fromisoformat(value).date()
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"special_work {field_name} 不是合法日期: {value!r} ({exc})",
            ) from exc
