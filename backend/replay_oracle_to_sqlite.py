"""
Oracle → SQLite 数据重放迁移脚本

不直接拷贝数据，而是从 Oracle 读取原始数据，通过 CRUD/Service 层在 SQLite 中重建所有记录。
这样 SQLAlchemy 自动处理所有格式、约束、关联关系。

使用方法：
  1. 在下方 CONFIG 区域填写 Oracle 连接信息
  2. cd backend/
  3. python replay_oracle_to_sqlite.py

依赖：pip install cx_Oracle
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

# ============================================================
# CONFIG - 在这里填写连接信息
# ============================================================

ORACLE_HOST = ""           # 例: "192.168.1.100"
ORACLE_PORT = "1521"
ORACLE_SERVICE = ""        # 例: "orcl"
ORACLE_USER = ""
ORACLE_PASSWORD = ""

SQLITE_DB_PATH = "taizhang.db"              # 迁移目标 SQLite 文件

# 内网 Casbin SQLite 文件路径（casbin_rule 表在这个文件里，其他业务数据在 Oracle）
CASBIN_DB_PATH = "casbin.db"                # 填内网的 Casbin SQLite 文件路径

# ============================================================
# 环境准备（必须在 import app 之前）
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("replay")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

os.environ.setdefault("DATABASE_TYPE", "sqlite")
os.environ.setdefault("ORACLE_USER", "")
os.environ.setdefault("ORACLE_PASSWORD", "")
os.environ.setdefault("ORACLE_SERVICE", "")

# ============================================================
# 工具函数
# ============================================================

# 全局 ID 映射: table_name -> {oracle_id: sqlite_id}
id_map: dict[str, dict[int, int]] = defaultdict(dict)


def read_lob(val):
    if val is None:
        return None
    if hasattr(val, "read"):
        val = val.read()
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    return val


def read_json_lob(val):
    """读取 Oracle CLOB 中的 JSON，标准化后返回 Python 对象（dict/list/None）"""
    val = read_lob(val)
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            log.warning("  无效 JSON（原样存入）: %.80s...", val)
            return val
    return val


def map_id(table: str, oracle_id) -> int | None:
    """将 Oracle ID 映射为 SQLite ID，找不到返回 None"""
    if oracle_id is None:
        return None
    result = id_map[table].get(int(oracle_id))
    if result is None:
        log.warning("  ID 映射缺失: %s.%s", table, oracle_id)
    return result


def ora_cols_str(cols: list[str]) -> str:
    """生成 Oracle SELECT 列列表，加双引号避免保留字"""
    return ", ".join(f'"{c}"' for c in cols)


def get_oracle_columns(cursor, table: str) -> list[str]:
    """获取 Oracle 表的列名（原始大小写）"""
    cursor.execute(
        "SELECT column_name FROM user_tab_columns "
        "WHERE table_name = UPPER(:t) ORDER BY column_id",
        {"t": table},
    )
    return [row[0] for row in cursor.fetchall()]


def oracle_query(cursor, table: str, columns: list[str], order_by: str = None):
    """执行 Oracle 查询，自动处理保留字"""
    cols = ora_cols_str(columns)
    sql = f"SELECT {cols} FROM {table}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    cursor.execute(sql)
    return cursor


# ============================================================
# 步骤 1: 角色
# ============================================================

def migrate_roles(ora_cur, db):
    from app import crud, schemas

    log.info("步骤 1/8: 迁移角色 ...")
    count = 0
    ora_cur_execute = oracle_query(
        ora_cur, "roles",
        ["ID", "NAME", "DESCRIPTION", "IS_SYSTEM"],
        '"ID"',
    )
    for row in ora_cur:
        oracle_id, name, description, is_system = row
        description = read_lob(description)

        existing = crud.role.get_by_name(db, name=name)
        if existing:
            id_map["roles"][oracle_id] = existing.id
            log.info("  角色已存在: %s (id=%d), 跳过", name, existing.id)
            continue

        role_in = schemas.RoleCreate(
            name=name,
            description=description,
            is_system=bool(is_system) if is_system is not None else False,
            permissions=[],
        )
        role = crud.role.create(db, obj_in=role_in)
        id_map["roles"][oracle_id] = role.id
        count += 1

    db.commit()
    log.info("  ✓ 角色迁移完成: 新建 %d 个", count)


# ============================================================
# 步骤 2: 团队
# ============================================================

def migrate_teams(ora_cur, db):
    from app import crud, schemas

    log.info("步骤 2/8: 迁移团队 ...")
    count = 0
    leader_fixups = []

    oracle_query(
        ora_cur, "teams",
        ["ID", "NAME", "DEPARTMENT", "DESCRIPTION", "LEADER_ID"],
        '"ID"',
    )
    for row in ora_cur:
        oracle_id, name, department, description, leader_id = row
        description = read_lob(description)

        existing = db.query(crud.team.model).filter(crud.team.model.name == name).first()
        if existing:
            id_map["teams"][oracle_id] = existing.id
            continue

        team_in = schemas.TeamCreate(
            name=name,
            department=department or "未指定",
            description=description,
        )
        team = crud.team.create(db, obj_in=team_in)
        id_map["teams"][oracle_id] = team.id

        if leader_id:
            leader_fixups.append((team.id, int(leader_id)))
        count += 1

    db.commit()
    log.info("  ✓ 团队迁移完成: 新建 %d 个, 待回填 leader %d 个", count, len(leader_fixups))
    return leader_fixups


# ============================================================
# 步骤 3: 用户
# ============================================================

def migrate_users(ora_cur, db):
    from app.models import User
    from app.core.security import get_password_hash

    log.info("步骤 3/8: 迁移用户 ...")
    count = 0

    oracle_query(
        ora_cur, "users",
        ["ID", "USERNAME", "EHR_ID", "HASHED_PASSWORD", "NAME",
         "DEPARTMENT", "IS_ACTIVE", "ISSUPERUSER", "TEAM_ID",
         "LAST_PASSWORD_CHANGE"],
        '"ID"',
    )
    for row in ora_cur:
        oracle_id, username, ehr_id, hashed_pw, name, \
            department, is_active, is_superuser, team_id, last_pwd_change = row

        hashed_pw = read_lob(hashed_pw)

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            id_map["users"][oracle_id] = existing.id
            continue

        user = User(
            username=username,
            ehr_id=ehr_id,
            hashed_password=hashed_pw or get_password_hash("default_password_123"),
            name=name,
            department=department,
            is_active=bool(is_active) if is_active is not None else True,
            is_superuser=bool(is_superuser) if is_superuser is not None else False,
            team_id=map_id("teams", team_id),
            last_password_change=last_pwd_change,
        )
        db.add(user)
        db.flush()
        id_map["users"][oracle_id] = user.id
        count += 1

    db.commit()
    log.info("  ✓ 用户迁移完成: 新建 %d 个", count)


def fixup_team_leaders(db, leader_fixups):
    """回填团队 leader_id"""
    from app.models import Team

    for sqlite_team_id, oracle_leader_id in leader_fixups:
        sqlite_leader_id = map_id("users", oracle_leader_id)
        if sqlite_leader_id:
            team = db.query(Team).get(sqlite_team_id)
            if team:
                team.leader_id = sqlite_leader_id
    db.commit()
    log.info("  ✓ 团队 leader_id 回填完成")


def migrate_casbin(db):
    """从内网 Casbin SQLite 读取策略，映射 user_id 后写入新 SQLite"""
    from app.services.casbin_service import get_enforcer_instance, add_role_for_user

    casbin_path = os.path.abspath(CASBIN_DB_PATH)
    if not os.path.exists(casbin_path):
        log.warning("  Casbin SQLite 文件不存在: %s，跳过策略迁移", casbin_path)
        return

    log.info("  从 Casbin SQLite 读取策略: %s", casbin_path)

    try:
        e = get_enforcer_instance()
    except Exception as e_err:
        log.warning("  Casbin 初始化失败: %s，跳过策略迁移", e_err)
        return

    casbin_conn = sqlite3.connect(casbin_path)
    casbin_cur = casbin_conn.cursor()

    # 权限策略 (p 类型: role, resource, action)
    p_count = 0
    try:
        casbin_cur.execute("SELECT v0, v1, v2 FROM casbin_rule WHERE ptype = 'p'")
        for role, resource, action in casbin_cur.fetchall():
            if not e.has_policy(role, resource, action):
                e.add_policy(role, resource, action)
                p_count += 1
    except Exception as e_err:
        log.warning("  Casbin 权限策略读取失败: %s", e_err)

    # 用户角色 (g 类型: user_id, role_name)
    g_count = 0
    try:
        casbin_cur.execute("SELECT v0, v1 FROM casbin_rule WHERE ptype = 'g'")
        for oracle_user_id_str, role_name in casbin_cur.fetchall():
            try:
                oracle_user_id = int(oracle_user_id_str)
            except (ValueError, TypeError):
                continue
            sqlite_user_id = map_id("users", oracle_user_id)
            if sqlite_user_id:
                add_role_for_user(str(sqlite_user_id), role_name)
                g_count += 1
    except Exception as e_err:
        log.warning("  Casbin 用户角色读取失败: %s", e_err)

    casbin_conn.close()
    log.info("  ✓ Casbin 迁移完成: 权限策略 %d 条, 用户角色 %d 条", p_count, g_count)


# ============================================================
# 步骤 4: 工作流 + 节点 + 审批人
# ============================================================

def migrate_workflows(ora_cur, db):
    from app import crud, schemas
    from app.models import WorkflowNode

    log.info("步骤 4/8: 迁移工作流 ...")

    # 4a. 工作流
    wf_count = 0
    oracle_query(
        ora_cur, "workflows",
        ["ID", "NAME", "DESCRIPTION", "IS_ACTIVE", "CREATED_BY"],
        '"ID"',
    )
    for row in ora_cur:
        oracle_id, name, description, is_active, created_by = row
        description = read_lob(description)
        creator_id = map_id("users", created_by)
        if not creator_id:
            continue

        wf_in = schemas.WorkflowCreate(
            name=name,
            description=description,
            is_active=bool(is_active) if is_active is not None else True,
            nodes=[],
        )
        wf = crud.workflow.create_with_nodes(db, obj_in=wf_in, created_by=creator_id)
        id_map["workflows"][oracle_id] = wf.id
        wf_count += 1

    db.commit()
    log.info("  工作流: 新建 %d 个", wf_count)

    # 4b. 工作流节点
    node_count = 0
    reject_fixups = []
    oracle_query(
        ora_cur, "workflow_nodes",
        ["ID", "WORKFLOW_ID", "NAME", "DESCRIPTION", "NODE_TYPE",
         "APPROVER_ROLE_ID", "ORDER_INDEX", "IS_FINAL",
         "REJECT_TO_NODE_ID", "MULTI_APPROVE_TYPE"],
        '"WORKFLOW_ID", "ORDER_INDEX"',
    )
    for row in ora_cur:
        oracle_id, wf_id, name, description, node_type, \
            approver_role_id, order_index, is_final, \
            reject_to_node_id, multi_approve_type = row

        description = read_lob(description)
        sqlite_wf_id = map_id("workflows", wf_id)
        if not sqlite_wf_id:
            continue

        node = WorkflowNode(
            workflow_id=sqlite_wf_id,
            name=name,
            description=description,
            node_type=node_type,
            approver_role_id=map_id("roles", approver_role_id),
            order_index=int(order_index) if order_index is not None else 0,
            is_final=bool(is_final) if is_final is not None else False,
            reject_to_node_id=None,  # 稍后回填
            multi_approve_type=multi_approve_type or "any",
        )
        db.add(node)
        db.flush()
        id_map["workflow_nodes"][oracle_id] = node.id

        if reject_to_node_id:
            reject_fixups.append((node.id, int(reject_to_node_id)))
        node_count += 1

    db.commit()

    # 回填 reject_to_node_id
    for sqlite_node_id, oracle_reject_id in reject_fixups:
        sqlite_reject_id = map_id("workflow_nodes", oracle_reject_id)
        if sqlite_reject_id:
            node = db.query(WorkflowNode).get(sqlite_node_id)
            if node:
                node.reject_to_node_id = sqlite_reject_id
    db.commit()

    log.info("  工作流节点: 新建 %d 个, reject 回填 %d 个", node_count, len(reject_fixups))

    # 4c. 审批人关联表
    approver_count = 0
    from app.models.workflow import workflow_node_approvers
    try:
        oracle_query(ora_cur, "workflow_node_approvers",
                     ["WORKFLOW_NODE_ID", "USER_ID"])
        for row in ora_cur:
            node_id, user_id = row
            sqlite_node_id = map_id("workflow_nodes", node_id)
            sqlite_user_id = map_id("users", user_id)
            if sqlite_node_id and sqlite_user_id:
                db.execute(
                    workflow_node_approvers.insert(),
                    {"workflow_node_id": sqlite_node_id, "user_id": sqlite_user_id},
                )
                approver_count += 1
        db.commit()
    except Exception as e_err:
        log.warning("  审批人关联表迁移失败: %s", e_err)
        db.rollback()

    log.info("  ✓ 工作流全部完成: 审批人关联 %d 条", approver_count)


# ============================================================
# 步骤 5: 模板 + 字段
# ============================================================

def migrate_templates(ora_cur, db):
    from app import crud, schemas
    from app.models import Field

    log.info("步骤 5/8: 迁移模板 ...")

    # 5a. 模板
    tpl_count = 0
    oracle_query(
        ora_cur, "templates",
        ["ID", "NAME", "DESCRIPTION", "DEPARTMENT", "IS_SYSTEM",
         "WORKFLOW_ID", "DEFAULT_DESCRIPTION", "DEFAULT_METADATA",
         "AUTO_FILL_CONFIG", "CREATED_BY_ID", "UPDATED_BY_ID"],
        '"ID"',
    )
    for row in ora_cur:
        oracle_id, name, description, department, is_system, \
            workflow_id, default_desc, default_metadata, auto_fill_config, \
            created_by_id, updated_by_id = row

        description = read_lob(description)
        default_desc = read_lob(default_desc)
        default_metadata = read_json_lob(default_metadata)
        auto_fill_config = read_json_lob(auto_fill_config)

        creator_id = map_id("users", created_by_id)
        if not creator_id:
            continue

        tpl_in = schemas.TemplateCreate(
            name=name,
            description=description,
            department=department or "未指定",
            is_system=bool(is_system) if is_system is not None else False,
            workflow_id=map_id("workflows", workflow_id),
            default_description=default_desc,
            default_metadata=default_metadata,
            auto_fill_config=auto_fill_config,
            fields=[],
        )
        tpl = crud.template.create(db, obj_in=tpl_in, creator_id=creator_id)
        id_map["templates"][oracle_id] = tpl.id
        tpl_count += 1

    db.commit()
    log.info("  模板: 新建 %d 个", tpl_count)

    # 5b. 字段
    field_count = 0
    oracle_query(
        ora_cur, "fields",
        ["ID", "NAME", "LABEL", "TYPE", "REQUIRED", "OPTIONS",
         "DEFAULT_VALUE", "ORDER", "IS_KEY_FIELD", "TEMPLATE_ID"],
        '"TEMPLATE_ID", "ORDER"',
    )
    for row in ora_cur:
        oracle_id, name, label, field_type, required, options, \
            default_value, order, is_key_field, template_id = row

        options = read_json_lob(options)
        sqlite_tpl_id = map_id("templates", template_id)
        if not sqlite_tpl_id:
            continue

        field = Field(
            name=name,
            label=label,
            type=field_type,
            required=bool(required) if required is not None else False,
            options=options,
            default_value=default_value,
            order=int(order) if order is not None else 0,
            is_key_field=bool(is_key_field) if is_key_field is not None else True,
            template_id=sqlite_tpl_id,
        )
        db.add(field)
        db.flush()
        id_map["fields"][oracle_id] = field.id
        field_count += 1

    db.commit()
    log.info("  ✓ 模板全部完成: 字段 %d 个", field_count)


# ============================================================
# 步骤 6: 台账
# ============================================================

def migrate_ledgers(ora_cur, db):
    from app import crud, schemas
    from app.models import Ledger
    from app.services.ledger_service import LedgerService

    log.info("步骤 6/8: 迁移台账 ...")
    count = 0

    oracle_query(
        ora_cur, "ledgers",
        ["ID", "NAME", "DESCRIPTION", "STATUS", "APPROVAL_STATUS",
         "TEAM_ID", "TEMPLATE_ID", "DATA",
         "CREATED_BY_ID", "UPDATED_BY_ID", "CURRENT_APPROVER_ID",
         "CREATED_AT", "UPDATED_AT", "SUBMITTED_AT", "APPROVED_AT"],
        '"ID"',
    )
    for row in ora_cur:
        try:
            oracle_id, name, description, status, approval_status, \
                team_id, template_id, data, \
                created_by_id, updated_by_id, current_approver_id, \
                created_at, updated_at, submitted_at, approved_at = row

            description = read_lob(description)
            data = read_json_lob(data)

            creator_id = map_id("users", created_by_id)
            if not creator_id:
                continue
            updater_id = map_id("users", updated_by_id) if updated_by_id else creator_id
            sqlite_tpl_id = map_id("templates", template_id) if template_id else None
            if not sqlite_tpl_id:
                log.warning("  台账 %s 的模板 %s 不存在，跳过", name, template_id)
                continue

            ledger_in = schemas.LedgerCreate(
                name=name,
                description=description,
                status=status or "draft",
                approval_status=approval_status or "draft",
                team_id=map_id("teams", team_id),
                template_id=sqlite_tpl_id,
                data=data,
            )

            ledger = crud.ledger.create(
                db,
                obj_in=ledger_in,
                created_by_id=creator_id,
                updated_by_id=updater_id,
            )

            # 回填 CRUD 层不会处理的字段
            ledger.current_approver_id = map_id("users", current_approver_id)
            ledger.status = status or "draft"
            ledger.approval_status = approval_status or "draft"
            if created_at:
                ledger.created_at = created_at
            if updated_at:
                ledger.updated_at = updated_at
            ledger.submitted_at = submitted_at
            ledger.approved_at = approved_at
            db.add(ledger)
            db.flush()

            id_map["ledgers"][oracle_id] = ledger.id

            # 同步字段值
            if data and sqlite_tpl_id:
                LedgerService.sync_field_values_with_ledger_data(db, ledger.id)

            count += 1
        except Exception as e_err:
            log.error("  台账 %s 迁移失败: %s", name, e_err)
            db.rollback()
            continue

    db.commit()
    log.info("  ✓ 台账迁移完成: 新建 %d 个", count)


# ============================================================
# 步骤 7: 完整审批流程重放
# ============================================================

def replay_approvals(ora_cur, db):
    from app.models import WorkflowInstance, WorkflowInstanceNode
    from app.schemas.workflow import WorkflowNodeApproval, WorkflowNodeRejection
    from app import crud

    log.info("步骤 7/8: 重放审批流程 ...")

    # 读取 Oracle 的 workflow_instances
    oracle_query(
        ora_cur, "workflow_instances",
        ["ID", "WORKFLOW_ID", "LEDGER_ID", "STATUS",
         "CURRENT_NODE_ID", "CREATED_BY",
         "CREATED_AT", "UPDATED_AT", "COMPLETED_AT"],
        '"ID"',
    )
    ora_instances = list(ora_cur)

    inst_count = 0
    skip_count = 0

    for inst_row in ora_instances:
        try:
            oracle_inst_id, wf_id, ledger_id, status, \
                current_node_id, created_by, \
                created_at, updated_at, completed_at = inst_row

            sqlite_wf_id = map_id("workflows", wf_id)
            sqlite_ledger_id = map_id("ledgers", ledger_id)
            sqlite_created_by = map_id("users", created_by)

            if not sqlite_wf_id or not sqlite_ledger_id or not sqlite_created_by:
                skip_count += 1
                continue

            # 创建 WorkflowInstance（模拟提交审批）
            instance = crud.workflow_instance.create_with_nodes(
                db,
                workflow_id=sqlite_wf_id,
                ledger_id=sqlite_ledger_id,
                created_by=sqlite_created_by,
            )

            # 回填时间戳
            if created_at:
                instance.created_at = created_at
            if updated_at:
                instance.updated_at = updated_at
            if completed_at:
                instance.completed_at = completed_at

            id_map["workflow_instances"][oracle_inst_id] = instance.id

            # 读取该实例的所有节点记录，按 Oracle 节点顺序排列
            oracle_query(
                ora_cur, "workflow_instance_nodes",
                ["ID", "WORKFLOW_INSTANCE_ID", "WORKFLOW_NODE_ID", "STATUS",
                 "APPROVER_ID", "COMMENT", "APPROVER_ACTIONS",
                 "CREATED_AT", "UPDATED_AT", "COMPLETED_AT"],
                '"WORKFLOW_INSTANCE_ID", "ID"',
            )
            # 只取当前实例的节点
            ora_nodes = [
                r for r in ora_cur
                if r[1] == oracle_inst_id
            ]

            # 建立 SQLite 的实例节点映射（workflow_node_id → instance_node）
            sqlite_inst_nodes = db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.workflow_instance_id == instance.id
            ).all()
            sqlite_node_map = {
                n.workflow_node_id: n for n in sqlite_inst_nodes
            }

            # 按顺序重放审批动作
            for node_row in ora_nodes:
                oracle_node_id, _, oracle_wf_node_id, node_status, \
                    approver_id, comment, approver_actions, \
                    node_created_at, node_updated_at, node_completed_at = node_row

                comment = read_lob(comment)
                approver_actions = read_json_lob(approver_actions)
                sqlite_wf_node_id = map_id("workflow_nodes", oracle_wf_node_id)
                if not sqlite_wf_node_id:
                    continue

                sqlite_inst_node = sqlite_node_map.get(sqlite_wf_node_id)
                if not sqlite_inst_node:
                    continue

                # 设置审批人
                sqlite_approver_id = map_id("users", approver_id) if approver_id else None
                if sqlite_approver_id:
                    sqlite_inst_node.approver_id = sqlite_approver_id

                # 重放审批动作
                if node_status == "approved" and sqlite_approver_id:
                    try:
                        approval_data = WorkflowNodeApproval(
                            comment=comment,
                            next_approver_id=None,
                        )
                        crud.workflow_instance.approve_current_node(
                            db,
                            instance_id=instance.id,
                            user_id=sqlite_approver_id,
                            comment=comment,
                        )
                    except Exception as e_err:
                        log.warning("  审批通过重放失败 (instance=%d, node=%d): %s",
                                    oracle_inst_id, oracle_node_id, e_err)

                elif node_status == "rejected" and sqlite_approver_id:
                    try:
                        crud.workflow_instance.reject_current_node(
                            db,
                            instance_id=instance.id,
                            user_id=sqlite_approver_id,
                            comment=comment,
                        )
                    except Exception as e_err:
                        log.warning("  审批拒绝重放失败 (instance=%d, node=%d): %s",
                                    oracle_inst_id, oracle_node_id, e_err)

                # 回填时间戳和 approver_actions
                if node_created_at:
                    sqlite_inst_node.created_at = node_created_at
                if node_updated_at:
                    sqlite_inst_node.updated_at = node_updated_at
                if node_completed_at:
                    sqlite_inst_node.completed_at = node_completed_at
                if approver_actions:
                    sqlite_inst_node.approver_actions = approver_actions

            # 回填最终状态
            if status:
                instance.status = status
            if completed_at:
                instance.completed_at = completed_at

            db.commit()
            inst_count += 1

        except Exception as e_err:
            log.error("  工作流实例 %d 重放失败: %s", oracle_inst_id, e_err)
            db.rollback()
            continue

    log.info("  ✓ 审批重放完成: 成功 %d 个, 跳过 %d 个", inst_count, skip_count)


# ============================================================
# 步骤 8: 日志
# ============================================================

def migrate_logs(ora_cur, db):
    from app.models import SystemLog, AuditLog

    log.info("步骤 8/8: 迁移日志 ...")

    # system_logs
    sys_count = 0
    try:
        oracle_query(
            ora_cur, "system_logs",
            ["ID", "USER_ID", "IP_ADDRESS", "USER_AGENT", "LEVEL",
             "MODULE", "ACTION", "RESOURCE_TYPE", "RESOURCE_ID",
             "MESSAGE", "DETAILS", "CREATED_AT"],
            '"ID"',
        )
        for row in ora_cur:
            _, user_id, ip_address, user_agent, level, \
                module, action, resource_type, resource_id, \
                message, details, created_at = row

            message = read_lob(message)
            details = read_json_lob(details)

            entry = SystemLog(
                user_id=map_id("users", user_id),
                ip_address=ip_address,
                user_agent=user_agent,
                level=level,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message,
                details=details,
                created_at=created_at,
            )
            db.add(entry)
            sys_count += 1
            if sys_count % 500 == 0:
                db.commit()
                log.info("    system_logs: 已迁移 %d 条 ...", sys_count)

        db.commit()
    except Exception as e_err:
        log.warning("  system_logs 迁移失败: %s", e_err)
        db.rollback()
        sys_count = 0

    # audit_logs
    audit_count = 0
    try:
        oracle_query(
            ora_cur, "audit_logs",
            ["ID", "USER_ID", "LEDGER_ID", "WORKFLOW_INSTANCE_ID",
             "ACTION", "STATUS_BEFORE", "STATUS_AFTER",
             "COMMENT", "CREATED_AT"],
            '"ID"',
        )
        for row in ora_cur:
            _, user_id, ledger_id, wf_instance_id, \
                action, status_before, status_after, \
                comment, created_at = row

            comment = read_lob(comment)

            entry = AuditLog(
                user_id=map_id("users", user_id),
                ledger_id=map_id("ledgers", ledger_id),
                workflow_instance_id=map_id("workflow_instances", wf_instance_id),
                action=action,
                status_before=status_before,
                status_after=status_after,
                comment=comment,
                created_at=created_at,
            )
            db.add(entry)
            audit_count += 1

        db.commit()
    except Exception as e_err:
        log.warning("  audit_logs 迁移失败: %s", e_err)
        db.rollback()
        audit_count = 0

    log.info("  ✓ 日志迁移完成: system_logs=%d, audit_logs=%d", sys_count, audit_count)


# ============================================================
# 主流程
# ============================================================

def migrate():
    if not all([ORACLE_HOST, ORACLE_SERVICE, ORACLE_USER]):
        log.error("请在脚本顶部 CONFIG 区域填写 Oracle 连接信息")
        sys.exit(1)

    log.info("=" * 60)
    log.info("Oracle → SQLite 数据重放迁移")
    log.info("=" * 60)

    # 连接 Oracle
    import cx_Oracle

    log.info("连接 Oracle ...")
    try:
        dsn = cx_Oracle.makedsn(ORACLE_HOST, int(ORACLE_PORT), service_name=ORACLE_SERVICE)
        ora_conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
        ora_cur = ora_conn.cursor()
        log.info("  Oracle 连接成功")
    except Exception as e:
        log.error("  Oracle 连接失败: %s", e)
        sys.exit(1)

    # 创建 SQLite 表结构 + Session
    log.info("准备 SQLite ...")
    from sqlalchemy import create_engine
    from app.db.session import Base
    import app.models  # noqa: F401

    sqlite_path = os.path.abspath(SQLITE_DB_PATH)
    engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, checkfirst=True)
    engine.dispose()

    from app.db.session import SessionLocal
    db = SessionLocal()

    try:
        # 按依赖顺序执行迁移
        migrate_roles(ora_cur, db)

        leader_fixups = migrate_teams(ora_cur, db)

        migrate_users(ora_cur, db)
        fixup_team_leaders(db, leader_fixups)
        migrate_casbin(db)

        migrate_workflows(ora_cur, db)
        migrate_templates(ora_cur, db)
        migrate_ledgers(ora_cur, db)
        replay_approvals(ora_cur, db)
        migrate_logs(ora_cur, db)

        # 验证
        log.info("=" * 60)
        log.info("迁移完成！")
        log.info("SQLite 文件: %s", sqlite_path)
        log.info("ID 映射统计:")
        for table, mapping in id_map.items():
            if mapping:
                log.info("  %-30s %d 条", table, len(mapping))
        log.info("=" * 60)

    except Exception as e:
        log.error("迁移过程出错: %s", e, exc_info=True)
    finally:
        ora_cur.close()
        ora_conn.close()
        db.close()


if __name__ == "__main__":
    migrate()
