"""
P0.7 activity_claim 审批通过后落子表 service (PRD §6.2 v2.1)

设计目标: B2 活动申报审批通过后, 自动在 portrait_activity_record 创建对应记录.
沿用 P8 联动模式 (commit 后再同步, 失败抛 500 显性化 - Rule 12)
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.portrait import models as portrait_models
# log_info 移到 caller 调用, 避免 SQLite 单文件下 system_logs 与主 session 抢锁


def sync_activity_claim_to_record(
    db: Session, *, submission: portrait_models.SubmissionRecord
) -> Optional[portrait_models.ActivityRecord]:
    """B2 活动申报审批通过后, 落 portrait_activity_record

    步骤:
      1. 解析 submission.payload (JSON 字符串)
      2. 找 submitter 对应 Profile (没有则创建空档案)
      3. 落 ActivityRecord
      4. 返回新 record (caller commit)

    失败规则 (Rule 12):
      - payload JSON 损坏: 抛 500
      - profile 创建失败: 抛 500
      - 必填字段缺失: 抛 500 (校验在前, 理论上不会到这)
    """
    try:
        payload = json.loads(submission.payload) if submission.payload else {}
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"activity_claim payload 解析失败: {exc}",
        ) from exc

    # 必填字段 (validate 阶段已保证, 此处防御性)
    required = ["activity_name", "activity_time", "activity_type", "organizer"]
    for f in required:
        if not payload.get(f):
            raise HTTPException(
                status_code=500,
                detail=f"activity_claim 落子表时缺少字段: {f}",
            )

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
            detail=f"activity_claim 落子表: submitter {submission.submitter_user_id} 不存在",
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

    # activity_time 是 ISO 字符串, 转 date
    activity_time_str = payload["activity_time"]
    if isinstance(activity_time_str, str):
        try:
            activity_time = datetime.strptime(activity_time_str, "%Y-%m-%d").date()
        except ValueError:
            # 兼容 ISO 8601
            activity_time = datetime.fromisoformat(activity_time_str).date()
    else:
        activity_time = activity_time_str

    activity = portrait_models.ActivityRecord(
        profile_id=profile.id,
        activity_name=payload["activity_name"],
        activity_time=activity_time,
        activity_type=payload["activity_type"],
        organizer=payload["organizer"],
        award_or_participation=payload.get("award_or_participation"),
        content=payload.get("content"),
        hours=payload.get("hours"),
        source_submission_id=submission.id,
    )
    db.add(activity)
    db.flush()
    db.refresh(activity)
    return activity
