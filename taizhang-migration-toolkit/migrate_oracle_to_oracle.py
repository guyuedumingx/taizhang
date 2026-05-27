"""
Oracle → Oracle 数据迁移脚本

使用方法：
  1. 确保 Python 环境有 cx_Oracle（pip install cx_Oracle）
  2. 设置环境变量（或修改下方配置）：
     - 源库：SOURCE_ORACLE_USER, SOURCE_ORACLE_PASSWORD, SOURCE_ORACLE_DSN
     - 目标库：TARGET_ORACLE_USER, TARGET_ORACLE_PASSWORD, TARGET_ORACLE_DSN
  3. 运行：python migrate_oracle_to_oracle.py

功能：
  - 从源 Oracle 读取所有业务表数据，批量写入目标 Oracle
  - 自动处理 CLOB（LOB 对象 .read()）
  - 自动处理 JSON 列（读取 → json.loads → json.dumps 标准化）
  - 自动处理 DateTime / Decimal 类型（Oracle → Oracle 原生兼容）
  - 自动跳过源库中不存在的列（填 NULL）
  - 按外键依赖顺序插入，保留原 ID
  - 迁移前按反向依赖顺序清空目标库（先子表后父表，避免外键冲突）
  - 迁移后自动更新目标 Oracle 的自增序列

注意事项：
  - 目标 Oracle 库应先通过 Alembic 或 init_db 创建好表结构
  - 运行前建议备份目标数据库
  - 默认会先按反向依赖顺序清空目标库所有业务表，再导入新数据
  - 两端 Oracle 版本建议相同或相近（同为 19c 等）
"""

import os
import sys
import json
import logging
from datetime import datetime
from decimal import Decimal

import cx_Oracle

# ============================================================
# 日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("migrate_ora2ora")

# ============================================================
# 配置区 —— 通过环境变量或直接修改
# ============================================================

# 源 Oracle 配置
SOURCE_ORACLE_CONFIG = {
    "user": os.getenv("SOURCE_ORACLE_USER", ""),
    "password": os.getenv("SOURCE_ORACLE_PASSWORD", ""),
    "dsn": os.getenv("SOURCE_ORACLE_DSN", ""),  # 格式: host:port/service_name
}

# 目标 Oracle 配置
TARGET_ORACLE_CONFIG = {
    "user": os.getenv("TARGET_ORACLE_USER", ""),
    "password": os.getenv("TARGET_ORACLE_PASSWORD", ""),
    "dsn": os.getenv("TARGET_ORACLE_DSN", ""),  # 格式: host:port/service_name
}

# 批量插入大小
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))

# 表迁移顺序（按外键依赖，必须严格遵守）
TABLE_ORDER = [
    "users",
    "teams",
    "roles",
    "templates",
    "fields",
    "workflows",
    "workflow_nodes",
    "workflow_node_approvers",
    "ledgers",
    "field_values",
    "workflow_instances",
    "workflow_instance_nodes",
    "system_logs",
    "audit_logs",
]

# 每张表的主键列名（用于序列更新）
PK_COLUMNS = {
    "users": "id",
    "teams": "id",
    "roles": "id",
    "templates": "id",
    "fields": "id",
    "workflows": "id",
    "workflow_nodes": "id",
    "ledgers": "id",
    "field_values": "id",
    "workflow_instances": "id",
    "workflow_instance_nodes": "id",
    "system_logs": "id",
    "audit_logs": "id",
}

# 源 Oracle 中可能不存在的列（后来加的，源表里没有这些列）
MISSING_IN_SOURCE = {
    "templates": ["auto_fill_config"],
    "users": ["email", "password_expired"],
}

# 这些列在代码中定义为 JSON，Oracle 中是 CLOB 存的 JSON 字符串
JSON_COLUMNS = {
    "ledgers": ["data"],
    "templates": ["default_metadata", "auto_fill_config"],
    "fields": ["options"],
    "workflow_instance_nodes": ["approver_actions"],
    "system_logs": ["details"],
}

# 这些列在代码中定义为 Text，Oracle 中是 CLOB
TEXT_COLUMNS = {
    "ledgers": ["description"],
    "templates": ["description", "default_description"],
    "teams": ["description"],
    "roles": ["description"],
    "field_values": ["value"],
    "workflow_instance_nodes": ["comment"],
    "system_logs": ["message"],
    "audit_logs": ["comment"],
}

# workflow_node_approvers 是关联表，没有自增 ID
NO_AUTO_INCREMENT = {"workflow_node_approvers"}

# 是否在迁移前按反向依赖顺序清空目标库所有业务表
# 强烈建议保持 true，避免迁移失败后残留脏数据
CLEAN_TARGET = os.getenv("CLEAN_TARGET", "true").lower() == "true"


# ============================================================
# 工具函数
# ============================================================

def read_lob(val):
    """处理 Oracle LOB 对象，转为 Python 字符串。"""
    if val is None:
        return None
    if hasattr(val, "read"):
        val = val.read()
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    return val


def convert_value(val, table, column):
    """
    转换单个值：
    1. LOB → 字符串
    2. JSON 列 → json.loads + json.dumps 标准化
    3. DateTime → 原样保留（Oracle 兼容）
    4. Decimal → float（避免 Oracle NUMBER 精度差异）
    5. 其他 → 原样
    """
    if val is None:
        return None

    # 第一步：LOB 处理
    val = read_lob(val)
    if val is None:
        return None

    # 第二步：JSON 列处理
    json_cols = JSON_COLUMNS.get(table, [])
    if column in json_cols:
        if isinstance(val, str) and val.strip():
            try:
                return json.dumps(json.loads(val), ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                return val  # 不是有效 JSON，原样返回
        return val

    # 第三步：DateTime 处理 —— Oracle → Oracle 原生兼容，直接保留
    # cx_Oracle 会返回 datetime 对象，绑定到目标 Oracle 时也能直接使用

    # 第四步：Decimal 处理（Oracle NUMBER 可能返回 Decimal）
    if isinstance(val, Decimal):
        # Oracle → Oracle，保留为 Decimal 让 cx_Oracle 自己处理绑定
        # 但如果目标列是 INTEGER，Decimal 也可以直接绑定
        return float(val)

    return val


def get_oracle_columns(cursor, table_name):
    """获取 Oracle 表的实际列名列表（小写）。"""
    cursor.execute(
        "SELECT column_name FROM user_tab_columns WHERE table_name = UPPER(:t) ORDER BY column_id",
        {"t": table_name},
    )
    return [row[0].lower() for row in cursor.fetchall()]


def count_table(cursor, table_name):
    """获取 Oracle 表的行数。"""
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def quoted_col(col):
    """为列名加双引号，避免 Oracle 保留字冲突（如 order, comment, user 等）。"""
    return f'"{col}"'


def cols_select(cols):
    """生成 SELECT 列列表，列名加双引号。"""
    return ", ".join(quoted_col(c) for c in cols)


def cols_insert(cols):
    """生成 INSERT 列列表，列名加双引号。"""
    return ", ".join(quoted_col(c) for c in cols)


def bind_vars(num):
    """生成 Oracle 绑定变量占位符列表。"""
    return ", ".join(f":{i+1}" for i in range(num))


def find_sequence(cursor, table_name, pk_column):
    """
    查找 Oracle 表对应的自增序列名。
    SQLAlchemy Oracle 方言默认创建 {table}_{column}_seq 格式的序列。
    """
    # 尝试常见命名模式
    patterns = [
        f"{table_name}_{pk_column}_seq",
        f"{table_name}_seq",
        f"{table_name}_{pk_column}_sequence",
    ]
    for pattern in patterns:
        cursor.execute(
            "SELECT sequence_name FROM user_sequences WHERE sequence_name = UPPER(:s)",
            {"s": pattern},
        )
        row = cursor.fetchone()
        if row:
            return row[0]

    # 模糊查找：任何包含表名的序列
    cursor.execute(
        "SELECT sequence_name FROM user_sequences WHERE sequence_name LIKE UPPER(:s)",
        {"s": f"%{table_name}%"},
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    return None


def update_sequence(cursor, seq_name, max_id):
    """
    更新 Oracle 序列，使其下一个值大于 max_id。
    兼容 Oracle 12c+ 和 18c+ 的不同语法。
    """
    if max_id is None or max_id == 0:
        return

    target_val = max_id + 1

    try:
        # 方法1：Oracle 18c+ 支持 RESTART
        cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART START WITH {target_val}")
        log.info("    序列 %s 已通过 RESTART 重置为 %d", seq_name, target_val)
        return
    except cx_Oracle.DatabaseError:
        pass  # 不支持 RESTART，回退到方法2

    # 方法2：兼容 Oracle 12c 及更早版本
    # 获取当前值
    cursor.execute(f"SELECT {seq_name}.NEXTVAL FROM dual")
    current_val = cursor.fetchone()[0]

    # 计算需要增加的增量
    increment = target_val - current_val
    if increment <= 0:
        # 序列值已经足够大，无需调整
        return

    # 临时修改增量为 (target - current)
    cursor.execute(f"ALTER SEQUENCE {seq_name} INCREMENT BY {increment}")
    # 执行一次 NEXTVAL 使序列跳到目标值
    cursor.execute(f"SELECT {seq_name}.NEXTVAL FROM dual")
    # 恢复增量为 1
    cursor.execute(f"ALTER SEQUENCE {seq_name} INCREMENT BY 1")
    log.info("    序列 %s 已通过 INCREMENT 调整为 %d", seq_name, target_val)


def clean_target(tgt_cur, tgt_conn):
    """
    按外键依赖反向顺序清空目标库所有业务表数据。

    反向顺序：先删子表（被引用的表后删），避免 ORA-02292 外键冲突。
    顺序：audit_logs → system_logs → ... → users
    """
    reversed_order = list(reversed(TABLE_ORDER))

    log.info("  按反向依赖顺序清空目标库（先子表后父表）:")
    total_deleted = 0

    for table in reversed_order:
        try:
            tgt_cur.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = tgt_cur.fetchone()[0]

            if row_count > 0:
                tgt_cur.execute(f"DELETE FROM {table}")
                tgt_conn.commit()
                total_deleted += row_count
                log.info("    %-30s 删除 %d 行", table, row_count)
            else:
                log.info("    %-30s 已为空，跳过", table)

        except Exception as e:
            log.warning("    %-30s 清空失败: %s", table, e)
            tgt_conn.rollback()
            # 继续尝试下一张表
            continue

    log.info("  目标库清理完成，共删除 %d 行", total_deleted)
    return total_deleted


# ============================================================
# 主逻辑
# ============================================================

def migrate():
    # 验证配置
    for label, cfg in [("源库", SOURCE_ORACLE_CONFIG), ("目标库", TARGET_ORACLE_CONFIG)]:
        if not cfg["user"] or not cfg["dsn"]:
            log.error("请配置 %s Oracle 连接信息", label)
            log.error("  环境变量: %s_ORACLE_USER / %s_ORACLE_PASSWORD / %s_ORACLE_DSN",
                      label[0].upper(), label[0].upper(), label[0].upper())
            log.error("  DSN 格式: host:port/service_name")
            sys.exit(1)

    log.info("=" * 60)
    log.info("Oracle → Oracle 数据迁移")
    log.info("=" * 60)
    log.info("源库 DSN:   %s", SOURCE_ORACLE_CONFIG["dsn"])
    log.info("目标库 DSN: %s", TARGET_ORACLE_CONFIG["dsn"])
    log.info("批量大小:   %d", BATCH_SIZE)
    log.info()

    # ----------------------------------------------------------
    # 步骤 1：连接源库
    # ----------------------------------------------------------
    log.info("[1/6] 连接源 Oracle ...")
    try:
        src_conn = cx_Oracle.connect(
            user=SOURCE_ORACLE_CONFIG["user"],
            password=SOURCE_ORACLE_CONFIG["password"],
            dsn=SOURCE_ORACLE_CONFIG["dsn"],
        )
        src_cur = src_conn.cursor()
        log.info("  源库连接成功")
    except Exception as e:
        log.error("  源库连接失败: %s", e)
        sys.exit(1)

    # ----------------------------------------------------------
    # 步骤 2：连接目标库
    # ----------------------------------------------------------
    log.info("[2/6] 连接目标 Oracle ...")
    try:
        tgt_conn = cx_Oracle.connect(
            user=TARGET_ORACLE_CONFIG["user"],
            password=TARGET_ORACLE_CONFIG["password"],
            dsn=TARGET_ORACLE_CONFIG["dsn"],
        )
        tgt_cur = tgt_conn.cursor()
        log.info("  目标库连接成功")
    except Exception as e:
        log.error("  目标库连接失败: %s", e)
        sys.exit(1)

    # ----------------------------------------------------------
    # 步骤 3：验证目标库表结构
    # ----------------------------------------------------------
    log.info("[3/6] 验证目标库表结构 ...")
    missing_tables = []
    for table in TABLE_ORDER:
        tgt_cols = get_oracle_columns(tgt_cur, table)
        if not tgt_cols:
            missing_tables.append(table)
    if missing_tables:
        log.error("  目标库缺少以下表: %s", ", ".join(missing_tables))
        log.error("  请先在目标库执行 Alembic 迁移或 init_db 创建表结构")
        src_cur.close()
        src_conn.close()
        tgt_cur.close()
        tgt_conn.close()
        sys.exit(1)
    log.info("  表结构验证通过，所有 %d 张表均存在", len(TABLE_ORDER))

    # ----------------------------------------------------------
    # 步骤 4：按反向依赖顺序清空目标库
    # ----------------------------------------------------------
    if CLEAN_TARGET:
        log.info("[4/6] 清空目标库数据（反向依赖顺序） ...")
        clean_target(tgt_cur, tgt_conn)
    else:
        log.info("[4/6] 跳过目标库清空（CLEAN_TARGET=false）")

    # ----------------------------------------------------------
    # 步骤 5：迁移数据
    # ----------------------------------------------------------
    log.info("[5/6] 开始迁移数据 ...")
    log.info("-" * 60)
    total_rows = 0

    for table in TABLE_ORDER:
        try:
            # 获取源库实际列
            src_cols = get_oracle_columns(src_cur, table)
            if not src_cols:
                log.info("  %s: 源库不存在此表，跳过", table)
                continue

            # 获取目标库实际列
            tgt_cols = get_oracle_columns(tgt_cur, table)
            if not tgt_cols:
                log.info("  %s: 目标库不存在此表，跳过", table)
                continue

            # 找出两边的交集列
            common_cols = [c for c in src_cols if c in tgt_cols]
            # 目标库中有但源库中没有的列（后来加的）
            extra_cols = [c for c in tgt_cols if c not in src_cols]

            # 行数统计
            row_count = count_table(src_cur, table)
            log.info(
                "  %s: 源库 %d 行, 匹配列 %d/%d",
                table, row_count, len(common_cols), len(tgt_cols),
            )

            if row_count == 0:
                log.info("    → 无数据，跳过")
                continue

            # 构建目标列列表：交集列 + 源库缺失列（填 NULL）
            insert_cols = common_cols + extra_cols

            # 从源库读取数据
            select_sql = f"SELECT {cols_select(common_cols)} FROM {table}"
            src_cur.execute(select_sql)

            # 批量插入目标库
            insert_sql = (
                f"INSERT INTO {table} ({cols_insert(insert_cols)}) "
                f"VALUES ({bind_vars(len(insert_cols))})"
            )

            batch = []
            inserted = 0

            for row in src_cur:
                values = []
                for col in insert_cols:
                    if col in common_cols:
                        idx = common_cols.index(col)
                        val = convert_value(row[idx], table, col)
                    else:
                        val = None  # 源库中不存在的列填 NULL
                    values.append(val)
                batch.append(tuple(values))

                if len(batch) >= BATCH_SIZE:
                    tgt_cur.executemany(insert_sql, batch)
                    tgt_conn.commit()
                    inserted += len(batch)
                    batch = []
                    log.info("    %s: 已插入 %d/%d 行 ...", table, inserted, row_count)

            if batch:
                tgt_cur.executemany(insert_sql, batch)
                tgt_conn.commit()
                inserted += len(batch)

            total_rows += inserted
            log.info("    → 迁移完成: %d 行", inserted)

        except Exception as e:
            log.error("    → 失败: %s", e)
            tgt_conn.rollback()
            continue

    log.info("-" * 60)
    log.info("  共迁移 %d 行数据", total_rows)

    # ----------------------------------------------------------
    # 步骤 6：更新目标库自增序列
    # ----------------------------------------------------------
    log.info("[6/6] 更新目标库自增序列 ...")
    seq_updated = 0
    for table in TABLE_ORDER:
        if table in NO_AUTO_INCREMENT:
            continue
        if table not in PK_COLUMNS:
            continue

        pk = PK_COLUMNS[table]
        try:
            tgt_cur.execute(f"SELECT MAX({quoted_col(pk)}) FROM {table}")
            result = tgt_cur.fetchone()
            max_id = result[0] if result else None

            if max_id is None:
                log.info("    %s: 无数据，跳过序列更新", table)
                continue

            # 查找序列
            seq_name = find_sequence(tgt_cur, table, pk)
            if seq_name:
                update_sequence(tgt_cur, seq_name, int(max_id))
                log.info("    %s: MAX(%s)=%d, 序列 %s 已更新", table, pk, max_id, seq_name)
                seq_updated += 1
            else:
                log.info("    %s: MAX(%s)=%d, 未找到序列（可能使用触发器或其他机制）", table, pk, max_id)

        except Exception as e:
            log.warning("    %s: 序列更新跳过 (%s)", table, e)

    tgt_conn.commit()
    log.info("  序列更新完成: %d 个", seq_updated)

    # ----------------------------------------------------------
    # 收尾
    # ----------------------------------------------------------
    src_cur.close()
    src_conn.close()
    tgt_cur.close()
    tgt_conn.close()

    log.info("")
    log.info("=" * 60)
    log.info("迁移完成！")
    log.info("  源库:   %s", SOURCE_ORACLE_CONFIG["dsn"])
    log.info("  目标库: %s", TARGET_ORACLE_CONFIG["dsn"])
    log.info("  总行数: %d", total_rows)
    log.info("")
    log.info("下一步：")
    log.info("  1. 验证目标库数据完整性")
    log.info("  2. 修改应用 .env 指向目标 Oracle")
    log.info("  3. 启动服务并测试功能")
    log.info("=" * 60)


if __name__ == "__main__":
    migrate()
