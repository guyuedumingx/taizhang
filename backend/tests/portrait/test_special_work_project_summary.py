"""
B1 专项工作审批通过 → 落 portrait_project_summary (2026-10-16 决策 3)

覆盖:
  - 落点正确: 写进画像自有的项目总结表, **不是**台账 ledgers
  - 字段映射: 用户名/时间/专项名称/专项内容/完成情况 五项对得上
  - 完成情况: 提交人填了用填的, 没填默认"已完成"
  - 不写台账: synced_ledger_id / workflow_instance_id 均不应被填
  - 幂等: 同一条 submission 不重复落表

⚠️ 本文件**不写开发库**, 用内存库 —— 审计 §6.6.1 已登记根 conftest 的 db 固件
   直连 taizhang.db 的问题。隔离写法 (两个 SessionLocal 都要换) 见该节。
"""
import random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.portrait import models as pmodels  # noqa: F401 触发 ORM 注册

client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


# ----------------------------------------------------------------- 隔离数据库
# 重构方案 Phase 1.1: 原自带内存库隔离 shim 已拆除 —— 根 tests/conftest.py 已推广
# 同款隔离 (并额外换掉 logger.py 的按值绑定), 用户固件改 function 级匹配根 db 固件。


@pytest.fixture(scope="function")
def admin_user(db: Session) -> models.User:
    user = models.User(
        username="admin_sw",
        ehr_id="2000001",
        name="审批管理员",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_headers(admin_user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(admin_user.id)})}"}


@pytest.fixture(scope="function")
def staff_user(db: Session) -> models.User:
    user = models.User(
        username="staff_sw",
        ehr_id="2000002",
        name="提交员工",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def staff_headers(staff_user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(staff_user.id)})}"}


def _ehr(db: Session) -> str:
    while True:
        e = str(random.randint(3000000, 8999999))
        if not db.query(models.User).filter(models.User.ehr_id == e).first():
            return e


@pytest.fixture(scope="function")
def submitter(db: Session):
    """每条用例一个全新的提交人, 避免互相干扰"""
    ehr = _ehr(db)
    u = models.User(
        username=f"sw_{ehr}",
        ehr_id=ehr,
        name="专项提交人",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture(scope="function")
def submitter_headers(submitter):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(submitter.id)})}"}


def _submit(headers: dict, approver, **payload_overrides) -> int:
    payload = {
        "project_name": "普惠金融专项",
        "start_time": "2026-03-01",
        "end_time": "2026-03-30",
        "content": "走访了 12 家网点",
        "hours": 24,
    }
    payload.update(payload_overrides)
    resp = client.post(
        f"{API_PORTRAIT}/submissions",
        headers=headers,
        json={
            "submission_type": "special_work",
            "payload": payload,
            "next_approver_id": approver.id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _approve(sub_id: int, headers: dict):
    resp = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=headers,
        json={"comment": "同意"},
    )
    assert resp.status_code == 200, resp.text


def _summary_for(db: Session, user) -> pmodels.ProjectSummary:
    s = (
        db.query(pmodels.ProjectSummary)
        .join(pmodels.Profile, pmodels.Profile.id == pmodels.ProjectSummary.profile_id)
        .filter(pmodels.Profile.user_id == user.id)
        .order_by(pmodels.ProjectSummary.id.desc())
        .first()
    )
    assert s is not None, f"用户 {user.id} 名下没有项目总结记录"
    return s


# ==================================================================== 测试
def test_approve_writes_project_summary(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """审批通过 → 记录落在画像自有的项目总结表, 五项字段对得上"""
    sub_id = _submit(submitter_headers, admin_user)
    _approve(sub_id, admin_headers)

    db.expire_all()
    s = _summary_for(db, submitter)

    assert s.project_name == "普惠金融专项", s.project_name
    assert s.start_time.isoformat() == "2026-03-01", s.start_time
    assert s.end_time.isoformat() == "2026-03-30", s.end_time
    assert s.description == "走访了 12 家网点", s.description
    # 用户名: 通过 profile_id 关联到提交人本人
    assert s.profile.user_id == submitter.id, "profile 没关联到提交人"
    # 预估工时必须有独立列, 不能塞进 role (那是静默损坏)
    # 注: payload 里 hours 是 JSON 数字, 但走过一层字符串化的表列, SQLite 又会
    # 弱类型存回文本, 所以按 int() 比较而不是直接 == 24。
    assert int(s.hours) == 24, f"预估工时应独立落列, 实际 role={s.role!r} hours={s.hours!r}"
    assert s.role is None, f"role 列不应被工时占用, 实际 {s.role!r}"


def test_completion_status_defaults_to_done(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """提交人没填完成情况 → 默认"已完成" (审批通过即视为完成)"""
    sub_id = _submit(submitter_headers, admin_user)
    _approve(sub_id, admin_headers)

    db.expire_all()
    assert _summary_for(db, submitter).completion_status == "已完成"


def test_completion_status_from_payload(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """提交人填了完成情况 → 用填的, 不被默认值覆盖"""
    sub_id = _submit(submitter_headers, admin_user, completion_status="已完成 80%")
    _approve(sub_id, admin_headers)

    db.expire_all()
    assert _summary_for(db, submitter).completion_status == "已完成 80%"


def test_does_not_write_ledger(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """决策 3 的核心: 不再写台账。synced_ledger_id / workflow_instance_id 都不该被填"""
    sub_id = _submit(submitter_headers, admin_user)
    _approve(sub_id, admin_headers)

    db.expire_all()
    sub = db.query(pmodels.SubmissionRecord).filter(
        pmodels.SubmissionRecord.id == sub_id
    ).first()

    assert sub.synced_ledger_id is None, (
        f"仍写了台账 ledger #{sub.synced_ledger_id}, 画像单独部署时台账表不存在"
    )
    assert sub.workflow_instance_id is None, (
        f"仍绑了台账 WorkflowInstance #{sub.workflow_instance_id}, 这是伪造的壳实例"
    )


def test_source_submission_id_links_back(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """来源 submission 要能反查, 否则档案里多出一条专项时无法追责"""
    sub_id = _submit(submitter_headers, admin_user)
    _approve(sub_id, admin_headers)

    db.expire_all()
    assert _summary_for(db, submitter).source_submission_id == sub_id


def test_no_duplicate_rows_for_same_submission(db: Session, submitter, submitter_headers, admin_user, admin_headers):
    """幂等: 重复触发联动不得落两行。

    直接调 service 两次模拟, 走 API 会被状态机挡住 (非 pending 不可审批),
    那样测不到 service 自身的幂等。
    """
    from app.portrait.services.special_work_sync_service import (
        sync_special_work_to_project_summary,
    )

    sub_id = _submit(submitter_headers, admin_user)
    _approve(sub_id, admin_headers)

    sub = db.query(pmodels.SubmissionRecord).filter(
        pmodels.SubmissionRecord.id == sub_id
    ).first()
    second = sync_special_work_to_project_summary(db, submission=sub)
    db.commit()

    assert second is None, "第二次联动应返回 None (幂等跳过), 实际又建了一条"

    db.expire_all()
    rows = (
        db.query(pmodels.ProjectSummary)
        .filter(pmodels.ProjectSummary.source_submission_id == sub_id)
        .all()
    )
    assert len(rows) == 1, f"同一条 submission 落了 {len(rows)} 行"


def test_missing_required_field_fails_loudly(db: Session, submitter, submitter_headers, admin_user):
    """payload 缺必填字段要显性报错, 不能静默写一行空记录 (Rule 12)"""
    from fastapi import HTTPException

    from app.portrait.services.special_work_sync_service import (
        sync_special_work_to_project_summary,
    )

    bad = pmodels.SubmissionRecord(
        submission_type="special_work",
        submitter_user_id=submitter.id,
        submitter_name=submitter.name,
        submitter_ehr_id=submitter.ehr_id,
        payload='{"start_time": "2026-03-01"}',  # 没有 project_name
        status="approved",
    )
    db.add(bad)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        sync_special_work_to_project_summary(db, submission=bad)
    assert exc.value.status_code == 500
    assert "project_name" in exc.value.detail
