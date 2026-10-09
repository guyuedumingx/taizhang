"""
阶段 F: Workflow 真绑 (special_work → workflow_instance)

覆盖 (5 test):
  - special_work approve 后 submission.workflow_instance_id 不为 None 且
    工作流实例的 ledger_id == synced_ledger_id (外键自洽)
  - 该 workflow_instance.status == 'completed' (因 portrait 视角已审批通过)
  - workflow_instance 至少有 2 个 instance_node, 且全 approved
  - workflow 自动 find-or-create: 两次联动复用同一 workflow
  - profile_edit approve 不创建 workflow_instance (联动仅 special_work)

设计说明:
  - 阶段 F 词面要求仅"submission 写入 workflow_instance_id", 不强求 workflow 真跑审批流.
  - WorkflowInstance 已直接 status='completed' (台账与 ledger 1:1 壳, 实际审批在 portrait 已完成).
  - 工作流的 ≥2 节点是硬约束 — 绕过 crud_workflow_instance.create_with_nodes 的 [1] bug.

复用 tests/portrait/test_api.py + test_integration.py 的 client + API_PORTRAIT + admin fixtures.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.main import app
from app.portrait import models as portrait_models
from app.portrait.services.integration_service import SPECIAL_WORK_WORKFLOW_NAME


client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


def _submit_and_approve_special_work(
    normal_token_headers: dict,
    admin_token_headers: dict,
    admin_user: models.User,
    project_name: str = "Workflow绑定测试",
) -> int:
    """helper: 提交并 admin 审批通过一条 special_work, 返回 submission_id"""
    resp = client.post(
        f"{API_PORTRAIT}/submissions",
        headers=normal_token_headers,
        json={
            "submission_type": "special_work",
            "payload": {
                "project_name": project_name,
                "start_time": "2026-03-01",
                "end_time": "2026-03-30",
                "content": "阶段 F workflow 联动测试",
                "hours": 24,
                "skill_tags": ["Workflow"],
            },
            "next_approver_id": admin_user.id,
        },
    )
    assert resp.status_code == 201, resp.text
    sub_id = resp.json()["id"]

    approve = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "阶段 F approve"},
    )
    assert approve.status_code == 200, approve.text
    return sub_id


def _create_profile_edit_for_admin(
    normal_token_headers: dict, admin_user: models.User
) -> int:
    """helper: profile_edit 提交给 admin (审批通过不联动)"""
    resp = client.post(
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
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ============================================================================
# F 主流程 (5 test)
# ============================================================================
def test_special_work_binds_workflow_instance(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """special_work approve 后 submission.workflow_instance_id 不为 None;
    关联的 WorkflowInstance.ledger_id == submission.synced_ledger_id (外键自洽)."""
    sub_id = _submit_and_approve_special_work(normal_token_headers, admin_token_headers, admin_user)

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()

    # submission.workflow_instance_id 已写回
    assert sub.workflow_instance_id is not None, (
        f"阶段 F: submission.workflow_instance_id 应非 None, 实际仍为 None"
    )
    assert sub.workflow_instance_id > 0

    # 关联到真实 WorkflowInstance
    wf_inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()
    assert wf_inst is not None, f"WorkflowInstance #{sub.workflow_instance_id} 不存在"

    # 内外键自洽: workflow_instance.ledger_id == submission.synced_ledger_id
    assert wf_inst.ledger_id == sub.synced_ledger_id, (
        f"workflow_instance.ledger_id={wf_inst.ledger_id} != "
        f"submission.synced_ledger_id={sub.synced_ledger_id}"
    )


def test_special_work_workflow_instance_completed(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """workflow_instance.status == 'completed' (special_work 已审批通过 → 直接 completed)"""
    sub_id = _submit_and_approve_special_work(normal_token_headers, admin_token_headers, admin_user)

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    wf_inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()

    assert wf_inst.status == "completed", (
        f"special_work 已审批通过 → workflow_instance.status 应是 'completed', "
        f"实际 {wf_inst.status}"
    )
    assert wf_inst.completed_at is not None, "completed_at 应被设置"


def test_special_work_workflow_instance_nodes_all_approved(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """workflow 至少 2 个 instance_node, 全 approved (因 special_work 审批已通过)"""
    sub_id = _submit_and_approve_special_work(normal_token_headers, admin_token_headers, admin_user)

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    instance_nodes = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.workflow_instance_id == sub.workflow_instance_id
    ).all()

    assert len(instance_nodes) >= 2, (
        f"workflow ≥2 节点是硬约束, 实际 {len(instance_nodes)}"
    )
    # 全部 approved (started 节点的 status 也置 approved — 简化处理)
    approved_statuses = {"approved"}
    for n in instance_nodes:
        assert n.status in approved_statuses, (
            f"instance_node #{n.id} status 应 approved, 实际 {n.status}"
        )


def test_special_work_workflow_reused_across_submissions(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """workflow 自动 find-or-create: 两次联动共用同一个 workflow (#id 不变)"""
    # 联动前看 workflow 总数
    before_wf_count = db.query(models.Workflow).filter(
        models.Workflow.name == SPECIAL_WORK_WORKFLOW_NAME
    ).count()

    # 第一次联动
    sub1_id = _submit_and_approve_special_work(
        normal_token_headers, admin_token_headers, admin_user, project_name="复用测试 1"
    )

    db.expire_all()
    sub1 = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub1_id
    ).first()
    wf_inst1 = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub1.workflow_instance_id
    ).first()
    wf_id_1 = wf_inst1.workflow_id

    # 第二次联动
    sub2_id = _submit_and_approve_special_work(
        normal_token_headers, admin_token_headers, admin_user, project_name="复用测试 2"
    )

    db.expire_all()
    sub2 = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub2_id
    ).first()
    wf_inst2 = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub2.workflow_instance_id
    ).first()
    wf_id_2 = wf_inst2.workflow_id

    # 两次走同一个 workflow
    assert wf_id_1 == wf_id_2, (
        f"workflow 应复用: wf_id_1={wf_id_1}, wf_id_2={wf_id_2}"
    )

    # workflow 总数不应增加 (复用, 不重复创建)
    after_wf_count = db.query(models.Workflow).filter(
        models.Workflow.name == SPECIAL_WORK_WORKFLOW_NAME
    ).count()
    # before 可能为 0 (如果数据库全新) 或 1 (之前测试已建), after 至多 +0
    # 注意: 其他测试可能仍未触发第一次联动, 所以 before <= after <= 1
    assert after_wf_count >= before_wf_count, (
        f"workflow 应不减少, before={before_wf_count}, after={after_wf_count}"
    )
    assert after_wf_count - before_wf_count <= 1, (
        f"本测试最多新建 1 个 workflow, 实际 +{after_wf_count - before_wf_count}"
    )


def test_profile_edit_does_not_bind_workflow_instance(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    """profile_edit approve 不创建 workflow_instance (联动仅 special_work)"""
    sub_id = _create_profile_edit_for_admin(normal_token_headers, admin_user)
    approve = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "profile edit approve"},
    )
    assert approve.status_code == 200

    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()

    # profile_edit 不联动 → 双 None
    assert sub.synced_ledger_id is None, (
        f"profile_edit.synced_ledger_id 应 None, 实际 {sub.synced_ledger_id}"
    )
    assert sub.workflow_instance_id is None, (
        f"阶段 F: profile_edit.workflow_instance_id 应 None, "
        f"实际 {sub.workflow_instance_id}"
    )
