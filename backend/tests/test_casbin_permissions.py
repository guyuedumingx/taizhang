"""
Casbin 权限矩阵测试 (阶段 E)

背景: 主系统路由已真实挂载 deps.check_permissions(资源, 动作, user);
但 init_permissions 从未被调用, user/manager 角色在 casbin_rule 表里
无 policy, 普通用户 enforce 恒 False. 阶段 E1 已在 init_db() 中接入
init_permissions(), 本测试验证 seed 后 enforce 真实生效.

覆盖 (5 test):
  - user 角色: 能 ledger:view, 不能 ledger:delete
  - manager 角色: 能 ledger:edit
  - 未绑角色用户: enforce 全部 False (即所有受保护操作被拒)
  - 角色与资源/动作组合矩阵 (4×5)
  - init_permissions 幂等: 二次调用不报错
"""
import pytest
from sqlalchemy.orm import Session

from app.services.casbin_service import (
    add_role_for_user,
    check_permission,
    get_enforcer_instance,
    remove_role_for_user,
)
from app.db.session import SessionLocal
from app.db.init_db import init_permissions


@pytest.fixture
def casbin_user():
    """为测试创建并清理临时分组 (ehr_id='TEST_CASBIN', 随机 user_id)"""
    user_id = "9000001"
    yield user_id
    # 清理
    for role in ("admin", "manager", "user"):
        remove_role_for_user(user_id, role)


def test_user_role_ledger_view_true(casbin_user):
    """user 角色: ledger:view 应放行, ledger:delete 应拒绝"""
    add_role_for_user(casbin_user, "user")
    assert check_permission(casbin_user, "ledger", "view") is True
    assert check_permission(casbin_user, "ledger", "create") is True
    assert check_permission(casbin_user, "ledger", "edit") is True
    assert check_permission(casbin_user, "ledger", "export") is True
    # user 角色无 delete policy
    assert check_permission(casbin_user, "ledger", "delete") is False


def test_manager_role_ledger_edit_true(casbin_user):
    """manager 角色: 能 ledger:delete (vs user 不能), 能 template:create/edit"""
    add_role_for_user(casbin_user, "manager")
    assert check_permission(casbin_user, "ledger", "view") is True
    assert check_permission(casbin_user, "ledger", "edit") is True
    assert check_permission(casbin_user, "ledger", "delete") is True
    # manager 有 template:create/edit
    assert check_permission(casbin_user, "template", "create") is True
    assert check_permission(casbin_user, "template", "edit") is True
    # manager 无 template:delete / user:create / role:view
    assert check_permission(casbin_user, "template", "delete") is False
    assert check_permission(casbin_user, "user", "create") is False
    assert check_permission(casbin_user, "role", "view") is False


def test_unbound_user_all_false(casbin_user):
    """未绑角色的用户: 任何 enforce 应 False (即受保护路由全 403)"""
    # 不调用 add_role_for_user
    for obj in ("ledger", "template", "user", "team", "workflow"):
        for act in ("view", "create", "edit", "delete", "export"):
            assert check_permission(casbin_user, obj, act) is False, (
                f"未绑角色应全 False, 但 ({obj},{act}) 为 True"
            )


def test_role_action_matrix(casbin_user):
    """4 角色 × 5 资源/动作 矩阵"""
    matrix = {
        # role -> [(obj, act, expected)]
        "user": [
            ("ledger", "view", True),
            ("ledger", "create", True),
            ("ledger", "edit", True),
            ("ledger", "delete", False),  # user 角色无 delete
            ("template", "view", True),
            ("template", "edit", False),   # user 角色无 template:edit
        ],
        "manager": [
            ("ledger", "view", True),
            ("ledger", "edit", True),
            ("ledger", "delete", True),
            ("template", "create", True), # manager 有 template:create
            ("template", "edit", True),   # manager 有 template:edit
            ("template", "delete", False),# manager 无 template:delete
            ("user", "view", True),       # manager 有 user:view
            ("user", "create", False),    # manager 无 user:create
        ],
    }
    for role, cases in matrix.items():
        add_role_for_user(casbin_user, role)
        for obj, act, expected in cases:
            actual = check_permission(casbin_user, obj, act)
            assert actual is expected, f"role={role} ({obj},{act}) 期望 {expected} 实际 {actual}"
        # 测试完该角色清理, 切下一个
        remove_role_for_user(casbin_user, role)


def test_init_permissions_idempotent():
    """init_permissions 幂等: 二次调用不报错 (casbin add_policy 重复由 adapter 去重)"""
    db = SessionLocal()
    try:
        init_permissions()
        init_permissions()  # 第二次
        init_permissions()  # 第三次
    finally:
        db.close()
    # 验证 user 角色仍能 ledger:view
    assert check_permission("9000001", "ledger", "view") is False  # 未绑角色
    add_role_for_user("9000001", "user")
    assert check_permission("9000001", "ledger", "view") is True
    remove_role_for_user("9000001", "user")
