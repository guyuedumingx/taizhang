"""
P3 阶段: portrait 4 套 Workflow 模板一次性初始化

集成指南 §3 阶段 3: 复用 taizhang Workflow 引擎, 配置 4 套 portrait 模板:
  - portrait_special_work  (专项工作)   1 个审批节点
  - portrait_home_visit    (家访)       1 个审批节点
  - portrait_profile_edit  (档案修改)   1 个审批节点
  - portrait_skill_tag_edit (亮点修改)  1 个审批节点

每个模板:
  - workflow (start -> approval -> end, 3 节点)
  - 审批节点的 approver_role_id 指向 admin 角色 (即 taizhang Role 表里 name='admin' 的 id)
  - 实际审批人由 portrait 业务决定 (special_work 用审批人下拉, 其他用 admin 角色)
  - 所有节点 multi_approve_type='any' (任一审批即可, 不需要全员)

执行:
    cd D:\\code\\taizhang\\backend
    python init_portrait_workflows.py            # 真初始化
    --dry-run                                   # 只打印计划, 不写入
    --reset                                     # 删除已有 portrait_* workflow 重新建

设计:
  ✅ 显式报告 created / skipped / errors 计数 (Rule 12)
  ✅ 失败节点不中断, 跳过并记录
  ✅ --dry-run 安全模式 (不动 DB)
  ✅ --reset 重置模式 (删 4 套重建, 不会破坏其它 workflow)

集成指南 §5 雷区合规:
  ✅ 1. 不改 Casbin rbac_model.conf (走 policy.csv)
  ✅ 2. 不 DROP workflow instances (--reset 只删 portrait_* 模板, 不动实例)
  ✅ 3. 不塞 portrait 字段进 ledger.data JSON
  ✅ 4. 不跨 schema 事务
  ✅ 5. 不改 JWT payload
  ✅ 6. 不改 ApprovalStatus 枚举 (本脚本不创建/修改枚举值)
  ✅ 7. 不绕过 Depends (本脚本不涉及 HTTP 鉴权)
"""
import argparse
import os
import sys
from typing import List, Optional, Tuple

# Windows GBK 编码兼容 (Rule 12: 错误明细必须可见)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 4 套模板定义 (PRD §9.1 4 类审批)
# 每套: (workflow_name, workflow_description, 节点列表)
#   节点: (name, node_type, order_index, is_final, multi_approve_type, approver_role_name)
PORTRAIT_WORKFLOWS = [
    (
        "portrait_special_work",
        "数字画像·专项工作审批 (员工提交项目工作, 选审批人下拉)",
        [
            ("提交", "start", 1, False, "any", None),
            ("审批", "approval", 2, False, "any", "admin"),
            ("完成", "end", 3, True, "any", None),
        ],
    ),
    (
        "portrait_home_visit",
        "数字画像·家访审批 (组长提交家访记录, 管理员审核归档)",
        [
            ("提交", "start", 1, False, "any", None),
            ("审批", "approval", 2, False, "any", "admin"),
            ("完成", "end", 3, True, "any", None),
        ],
    ),
    (
        "portrait_profile_edit",
        "数字画像·档案字段修改审批 (员工/组长提交档案修改, 管理员审批)",
        [
            ("提交", "start", 1, False, "any", None),
            ("审批", "approval", 2, False, "any", "admin"),
            ("完成", "end", 3, True, "any", None),
        ],
    ),
    (
        "portrait_skill_tag_edit",
        "数字画像·亮点标签修改审批 (员工提交高敏感标签, 管理员审批)",
        [
            ("提交", "start", 1, False, "any", None),
            ("审批", "approval", 2, False, "any", "admin"),
            ("完成", "end", 3, True, "any", None),
        ],
    ),
]


def get_admin_role_id(db) -> Optional[int]:
    """查 taizhang Role 表里 name='admin' 的 id. 找不到返回 None."""
    from app.models.role import Role
    admin = db.query(Role).filter(Role.name == "admin").first()
    return admin.id if admin else None


def workflow_exists(db, name: str) -> bool:
    """是否已存在同名 workflow 模板"""
    from app.models.workflow import Workflow
    return db.query(Workflow).filter(Workflow.name == name).first() is not None


def create_workflow_template(db, name: str, description: str, nodes_def: list, admin_role_id: int, created_by: int, dry_run: bool = False):
    """创建单个 workflow 模板 + 节点"""
    from app.models.workflow import Workflow, WorkflowNode

    if dry_run:
        print(f"[DRY-RUN] 将创建 workflow: {name}")
        for n in nodes_def:
            print(f"           节点: {n[0]} ({n[1]}, order={n[2]}, is_final={n[3]})")
        return "created_dry_run"

    wf = Workflow(
        name=name,
        description=description,
        is_active=True,
        created_by=created_by,
    )
    db.add(wf)
    db.flush()  # 拿 wf.id

    for node_def in nodes_def:
        node_name, node_type, order_index, is_final, multi_approve_type, approver_role_name = node_def
        approver_role_id = admin_role_id if approver_role_name == "admin" else None
        node = WorkflowNode(
            workflow_id=wf.id,
            name=node_name,
            node_type=node_type,
            order_index=order_index,
            is_final=is_final,
            multi_approve_type=multi_approve_type,
            approver_role_id=approver_role_id,
        )
        db.add(node)

    db.commit()
    return "created"


def reset_portrait_workflows(db, dry_run: bool = False) -> List[str]:
    """删除所有 portrait_ 前缀的 workflow 模板 + 节点 (实例不动, 符合雷区 2)"""
    from app.models.workflow import Workflow, WorkflowNode

    portrait_wfs = db.query(Workflow).filter(Workflow.name.like("portrait_%")).all()
    errors = []
    if not portrait_wfs:
        return ["无 portrait_ 前缀 workflow 需要清理"]

    for wf in portrait_wfs:
        if dry_run:
            print(f"[DRY-RUN] 将删除 workflow: {wf.name} (id={wf.id})")
            continue
        try:
            # 先删节点 (级联, 但显式删更稳)
            db.query(WorkflowNode).filter(WorkflowNode.workflow_id == wf.id).delete()
            db.delete(wf)
            db.commit()
            print(f"  删除: {wf.name} (id={wf.id})")
        except Exception as e:
            db.rollback()
            errors.append(f"删除 {wf.name} 失败: {type(e).__name__}: {e}")

    return errors


def init_portrait_workflows(dry_run: bool = False, reset: bool = False) -> Tuple[int, int, List[str]]:
    """初始化 4 套 portrait Workflow 模板

    Returns: (created, skipped, errors)
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.db.session import SessionLocal, Base
    import app.models  # noqa
    import app.portrait.models  # noqa

    created, skipped = 0, 0
    errors: List[str] = []

    if not dry_run:
        # 仅当非 dry-run 才创建表 (portrait_xxx 表可能还没建)
        from app.db.session import engine
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if reset:
            reset_errors = reset_portrait_workflows(db, dry_run=dry_run)
            errors.extend(reset_errors)

        admin_role_id = get_admin_role_id(db)
        if admin_role_id is None:
            errors.append("taizhang Role 表里没找到 name='admin' 的角色, 请先跑 init_db.py 初始化")
            return 0, 0, errors

        # 找台账第一个用户当 created_by (portrait 没自己的用户, 用台账 admin 用户)
        from app.models.user import User
        admin_user = db.query(User).filter(User.is_superuser == True).first()  # noqa: E712
        if not admin_user:
            errors.append("taizhang users 表里没有 superuser, 请先跑 init_db.py")
            return 0, 0, errors
        created_by = admin_user.id

        for name, description, nodes_def in PORTRAIT_WORKFLOWS:
            if workflow_exists(db, name):
                if reset:
                    # reset 已删除, 这里继续创建
                    pass
                else:
                    errors.append(f"{name} 已存在, 跳过 (用 --reset 重置)")
                    skipped += 1
                    continue

            try:
                result = create_workflow_template(
                    db, name, description, nodes_def, admin_role_id, created_by, dry_run
                )
                if result == "created" or result == "created_dry_run":
                    created += 1
                else:
                    skipped += 1
            except Exception as e:
                db.rollback()
                errors.append(f"{name}: {type(e).__name__}: {e}")
                skipped += 1
    finally:
        db.close()

    return created, skipped, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="P3 阶段: portrait 4 套 Workflow 模板初始化")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不写入")
    parser.add_argument("--reset", action="store_true", help="删除已有 portrait_ 模板重建")
    args = parser.parse_args()

    print("=== P3 阶段: portrait 4 套 Workflow 模板初始化 ===")
    print(f"目标 DB: taizhang 当前配置")
    print(f"模式: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    if args.reset:
        print(f"重置: 先删 portrait_ 前缀 workflow 再重建")
    print()

    created, skipped, errors = init_portrait_workflows(dry_run=args.dry_run, reset=args.reset)

    print(f"\n=== 初始化完成 ===")
    print(f"  created: {created}")
    print(f"  skipped: {skipped}")
    print(f"  errors:  {len(errors)}")
    if errors:
        print(f"\n--- 错误明细 ---")
        for e in errors:
            print(f"  ❌ {e}")

    if errors:
        print(f"\n⚠️  有 {len(errors)} 条问题, 请处理后回归")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())