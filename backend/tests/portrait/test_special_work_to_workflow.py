"""Phase 2: 画像提交 ↔ 台账 Workflow 引擎真实绑定测试

历史: 本文件原先测的是"假实例"机制 —— sync_special_work_to_ledger 在审批
通过后手工造一个直接 completed 的壳 WorkflowInstance 回填 submission。
Phase 2 (2026-10-20) 拆除该机制, submission 在创建时即绑定真实实例,
审批推进/终态由引擎管理。本文件改为验证真实路径:

  - 提交即建实例 (active, approval 节点 PENDING, 审批人直落节点)
  - 审批通过 → 引擎推进 → 实例 completed + 画像镜像同步
  - 模板跨提交复用 (同名模板不重复建)
  - profile_edit 同样走真实绑定
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.main import app
from app.portrait import models as portrait_models

client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


def _submit_special_work(normal_token_headers: dict, admin_user: models.User, name="Workflow绑定测试") -> int:
    resp = client.post(
        f"{API_PORTRAIT}/submissions",
        headers=normal_token_headers,
        json={
            "submission_type": "special_work",
            "payload": {
                "project_name": name,
                "start_time": "2026-03-01",
                "end_time": "2026-03-30",
                "content": "Phase 2 真实绑定测试",
                "hours": 24,
            },
            "next_approver_id": admin_user.id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _submit_profile_edit(normal_token_headers: dict, admin_user: models.User) -> int:
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


def _approve(sub_id: int, admin_token_headers: dict):
    return client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/approve",
        headers=admin_token_headers,
        json={"comment": "同意"},
    )


def _load_sub(db: Session, sub_id: int) -> portrait_models.SubmissionRecord:
    db.expire_all()
    sub = db.query(portrait_models.SubmissionRecord).filter(
        portrait_models.SubmissionRecord.id == sub_id
    ).first()
    assert sub is not None
    return sub


# ----------------------------------------------------------- 1. 提交即建实例
def test_submit_creates_active_instance(
    db: Session, normal_token_headers: dict, admin_user: models.User
):
    sub_id = _submit_special_work(normal_token_headers, admin_user)
    sub = _load_sub(db, sub_id)

    assert sub.workflow_instance_id is not None, "Phase 2: 提交即应绑定真实实例"
    inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()
    assert inst is not None
    assert inst.status == "active"
    assert inst.subject_type == "portrait_submission"
    assert inst.subject_id == sub.id
    assert inst.ledger_id is None, "画像实例不绑台账"

    # 审批人直落 approval 节点 (引擎权限判定依据)
    assert inst.current_node_id is not None
    node = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.id == inst.current_node_id
    ).first()
    assert node is not None and node.status == "pending"
    assert node.approver_id == admin_user.id


# ----------------------------------------------------------- 2. 审批 → 终态一致
def test_approve_completes_instance_and_mirror(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    sub_id = _submit_special_work(normal_token_headers, admin_user)
    resp = _approve(sub_id, admin_token_headers)
    assert resp.status_code == 200, resp.text

    sub = _load_sub(db, sub_id)
    assert sub.status == "approved", "画像镜像应同步为 approved"

    inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()
    assert inst.status == "completed"
    assert inst.completed_at is not None

    nodes = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.workflow_instance_id == inst.id
    ).all()
    assert len(nodes) >= 2
    for n in nodes:
        assert n.status in ("approved",), f"节点 #{n.id} 应为 approved, 实际 {n.status}"
    # approval 节点留有引擎的操作记录
    approval_nodes = [n for n in nodes if n.approver_actions]
    assert approval_nodes, "审批动作应写入 approver_actions"


# ----------------------------------------------------------- 3. 驳回路径
def test_reject_terminal_state_consistent(
    db: Session, admin_token_headers: dict, normal_token_headers: dict, admin_user: models.User
):
    sub_id = _submit_special_work(normal_token_headers, admin_user)
    resp = client.post(
        f"{API_PORTRAIT}/approvals/{sub_id}/reject",
        headers=admin_token_headers,
        json={"comment": "材料不全, 驳回"},
    )
    assert resp.status_code == 200, resp.text

    sub = _load_sub(db, sub_id)
    assert sub.status == "rejected"
    inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()
    assert inst.status == "rejected"


# ----------------------------------------------------------- 4. 模板复用
def test_template_reused_across_submissions(
    db: Session, normal_token_headers: dict, admin_user: models.User
):
    id1 = _submit_special_work(normal_token_headers, admin_user, name="复用A")
    id2 = _submit_special_work(normal_token_headers, admin_user, name="复用B")
    sub1, sub2 = _load_sub(db, id1), _load_sub(db, id2)
    assert sub1.workflow_instance_id != sub2.workflow_instance_id, "两次提交应是两个实例"

    inst1 = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub1.workflow_instance_id
    ).first()
    inst2 = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub2.workflow_instance_id
    ).first()
    assert inst1.workflow_id == inst2.workflow_id, "同名模板应复用, 不应重复建"
    wf = db.query(models.Workflow).filter(models.Workflow.id == inst1.workflow_id).first()
    assert wf.name == "portrait_special_work"


# ----------------------------------------------------------- 5. profile_edit 同样真绑
def test_profile_edit_binds_real_instance(
    db: Session, normal_token_headers: dict, admin_user: models.User
):
    """旧断言 (不绑实例) 是假实例时代防止壳实例污染的守卫;
    Phase 2 后 profile_edit 提交同样绑定真实实例。"""
    sub_id = _submit_profile_edit(normal_token_headers, admin_user)
    sub = _load_sub(db, sub_id)

    assert sub.workflow_instance_id is not None
    inst = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.id == sub.workflow_instance_id
    ).first()
    assert inst.subject_type == "portrait_submission"
    assert inst.status == "active"
