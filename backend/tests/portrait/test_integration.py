"""
P8 阶段: special_work 审批通过 → 自动联动台账 测试 (批次 14)

覆盖 (4 test):
  - special_work approve 后 DB 多 1 条 ledger, 含 __portrait_source__ 标记
  - ledger.data 保留 payload 全量字段
  - profile_edit approve 不联动 (只 special_work)
  - 模板自动 find-or-create (第一次联动创建, 后续复用)

复用 tests/portrait/test_api.py 的 client + API_PORTRAIT + admin fixtures
"""
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.main import app
from app.portrait import models as portrait_models


client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


def _create_special_work_for_admin(
    normal_token_headers: dict, admin_user: models.User, project_name: str = "联动测试项目"
) -> int:
    """helper: 创建 special_work 提交给 admin 审批"""
    response = client.post(
        f"{API_PORTRAIT}/submissions",
        headers=normal_token_headers,
        json={
            "submission_type": "special_work",
            "payload": {
                "project_name": project_name,
                "start_time": "2026-02-01",
                "end_time": "2026-02-28",
                "content": "P8 联动测试内容",
                "hours": 16,
                "skill_tags": ["Python", "联动"],
            },
            "next_approver_id": admin_user.id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_profile_edit_for_admin(
    normal_token_headers: dict, admin_user: models.User
) -> int:
    """helper: 创建 profile_edit 提交给 admin"""
    response = client.post(
        f"{API_PORTRAIT}/submissions",
        headers=normal_token_headers,
        json={
            "submission_type": "profile_edit",
            "payload": {
                "field_name": "job_title",
                "old_value": "员工",
                "new_value": "高级员工",
            },
            "next_approver_id": admin_user.id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ============================================================================
# 联动主流程 (4 test)
# ============================================================================
def test_special_work_approve_creates_ledger(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """special_work approve 后, ledgers 表 +1 新行"""
    # 记录 approve 前的 ledger 总数
    before_count = db.query(models.Ledger).count()

    # 提交 + 审批
    sub_id = _create_special_work_for_admin(normal_token_headers, admin_user)
    approve_resp = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "P8 approve test"},
    )
    assert approve_resp.status_code == 200, approve_resp.text

    # 验证 ledger +1
    after_count = db.query(models.Ledger).count()
    assert after_count == before_count + 1, (
        f"ledger 应 +1, before={before_count}, after={after_count}"
    )

    # 验证 submission.synced_ledger_id 写回
    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    assert sub.synced_ledger_id is not None
    assert sub.synced_ledger_id > 0


def test_special_work_ledger_data_contains_payload_and_source(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """ledger.data 含 payload 全量字段 + __portrait_source__ 标记 (雷区 3 合规)"""
    sub_id = _create_special_work_for_admin(
        normal_token_headers, admin_user, project_name="数据完整性测试"
    )
    approve_resp = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "approve for data check"},
    )
    assert approve_resp.status_code == 200

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    new_ledger = db.query(models.Ledger).filter(
        models.Ledger.id == sub.synced_ledger_id
    ).first()
    assert new_ledger is not None

    # ledger.name = payload.project_name
    assert new_ledger.name == "数据完整性测试"

    # ledger.data 含 __portrait_source__
    data = new_ledger.data
    assert isinstance(data, dict)
    assert "__portrait_source__" in data
    src = data["__portrait_source__"]
    assert src["submission_id"] == sub_id
    assert src["submission_type"] == "special_work"
    assert src["submitter_user_id"] > 0

    # payload 字段保留
    assert data["project_name"] == "数据完整性测试"
    assert data["hours"] == 16
    assert data["skill_tags"] == ["Python", "联动"]
    assert data["start_time"] == "2026-02-01"


def test_profile_edit_approve_does_not_create_ledger(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """profile_edit approve 不联动台账 (联动仅 special_work)"""
    before_count = db.query(models.Ledger).count()

    sub_id = _create_profile_edit_for_admin(normal_token_headers, admin_user)
    approve_resp = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "profile edit approve"},
    )
    assert approve_resp.status_code == 200

    after_count = db.query(models.Ledger).count()
    assert after_count == before_count, (
        f"profile_edit 不应联动台账, before={before_count}, after={after_count}"
    )

    # submission.synced_ledger_id 应为 None
    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    assert sub.synced_ledger_id is None


def test_special_work_template_auto_created_and_reused(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """专用模板"数字画像-专项工作"自动 find-or-create, 两次联动复用同一模板"""
    # 联动前先看模板数量
    before_tmpl_count = db.query(models.Template).filter(
        models.Template.name == "数字画像-专项工作"
    ).count()

    # 第一次联动
    sub1_id = _create_special_work_for_admin(
        normal_token_headers, admin_user, project_name="模板复用测试 1"
    )
    client.post(
        f"{API_PORTRAIT}/approvals/{sub1_id}/approve",
        headers=admin_token_headers,
        json={"comment": "first"},
    )

    db.expire_all()
    sub1 = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub1_id
    ).first()
    ledger1 = db.query(models.Ledger).filter(
        models.Ledger.id == sub1.synced_ledger_id
    ).first()
    tmpl1_id = ledger1.template_id

    # 第二次联动
    sub2_id = _create_special_work_for_admin(
        normal_token_headers, admin_user, project_name="模板复用测试 2"
    )
    client.post(
        f"{API_PORTRAIT}/approvals/{sub2_id}/approve",
        headers=admin_token_headers,
        json={"comment": "second"},
    )

    db.expire_all()
    sub2 = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub2_id
    ).first()
    ledger2 = db.query(models.Ledger).filter(
        models.Ledger.id == sub2.synced_ledger_id
    ).first()
    tmpl2_id = ledger2.template_id

    # 两次联动用同一个模板
    assert tmpl1_id == tmpl2_id, (
        f"模板应复用, tmpl1={tmpl1_id}, tmpl2={tmpl2_id}"
    )

    # 模板总数至少保留 (不重复创建; 之前测试可能已留过 1 个)
    after_tmpl_count = db.query(models.Template).filter(
        models.Template.name == "数字画像-专项工作"
    ).count()
    assert after_tmpl_count >= before_tmpl_count, (
        f"模板不应减少, before={before_tmpl_count}, after={after_tmpl_count}"
    )


def test_special_work_reapprove_is_idempotent(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """已 approved 的 special_work 再 approve 不重复创建 ledger (幂等)"""
    sub_id = _create_special_work_for_admin(
        normal_token_headers, admin_user, project_name="幂等测试"
    )
    # 第一次 approve (审批成功 → 自动联动)
    r1 = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "first"},
    )
    assert r1.status_code == 200

    # 手动 reset status 为 pending, 模拟"再审批"
    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    first_synced_id = sub.synced_ledger_id
    sub.status = "pending"
    sub.current_approver_id = admin_user.id
    db.commit()

    # 第二次 approve
    before_count = db.query(models.Ledger).count()
    r2 = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "second"},
    )
    # approve endpoint 不应拒绝 approved → pending 改回后再 approve
    # 但 service._ensure_can_act 检查 status == TERMINAL 时抛 400
    # 实际: 重置 status='pending' 后再 approve 合法, 但 synced_ledger_id 已有 → 跳过联动
    assert r2.status_code == 200, r2.text
    after_count = db.query(models.Ledger).count()
    assert after_count == before_count, (
        f"幂等: 第二次 approve 不应 +1 ledger, before={before_count}, after={after_count}"
    )

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    # synced_ledger_id 仍指向第一次创建的 ledger
    assert sub.synced_ledger_id == first_synced_id