"""
Oracle → SQLite 数据迁移脚本

使用方法：
  1. 确保 Python 环境有 cx_Oracle（pip install cx_Oracle）
  2. 修改下方 ORACLE_CONFIG 中的连接信息
  3. 修改 SQLITE_DB_PATH 为目标 SQLite 文件路径
  4. 运行：python migrate_oracle_to_sqlite.py

功能：
  - 自动从 Oracle 读取所有业务表数据
  - 自动处理 CLOB（LOB 对象 .read()）
  - 自动处理 JSON 列（字符串 → json.loads → json.dumps 标准化）
  - 自动处理 DateTime（datetime 对象 → ISO 字符串）
  - 自动跳过 Oracle 中不存在的列（填 NULL）
  - 按外键依赖顺序插入，保留原 ID
  - 更新 sqlite_sequence 使自增 ID 续接
  - 跳过已存在的表（保留 casbin_rule 等已有数据）

注意事项：
  - 目标 SQLite 文件如果已存在 casbin_rule 数据，不会被删除
  - 运行前建议备份目标 SQLite 文件
  - 如果某个表已有数据，会先清空再导入（不影响 casbin_rule）
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from decimal import Decimal

import cx_Oracle

# ============================================================
# 配置区 —— 修改这里
# ============================================================

ORACLE_CONFIG = {
    "user": os.getenv("ORACLE_USER", ""),
    "password": os.getenv("ORACLE_PASSWORD", ""),
    "dsn": os.getenv("ORACLE_DSN", ""),  # 格式: host:port/service_name
}

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "taizhang.db")

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

# 每张表的主键列名（用于 sqlite_sequence 更新）
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

# 在 Oracle 中可能不存在的列（后来加的，Oracle 表里没有这些列）
MISSING_IN_ORACLE = {
    "templates": ["auto_fill_config"],
    "users": ["email", "password_expired"],
}

# 这些列在代码中定义为 JSON，Oracle 中是 CLOB 存的 JSON 字符串
# 需要读取后 json.loads + json.dumps 标准化
JSON_COLUMNS = {
    "ledgers": ["data"],
    "templates": ["default_metadata", "auto_fill_config"],
    "fields": ["options"],
    "workflow_instance_nodes": ["approver_actions"],
    "system_logs": ["details"],
}

# 这些列在代码中定义为 Text，Oracle 中是 CLOB
# 只需要 .read() 读出字符串即可
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
    2. JSON 列 → json.loads + json.dumps
    3. DateTime → ISO 字符串
    4. Decimal → float
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
                return json.dumps(json.loads(val))
            except (json.JSONDecodeError, ValueError):
                return val  # 不是有效 JSON，原样返回
        return val

    # 第三步：DateTime 处理
    if isinstance(val, datetime):
        return val.isoformat()

    # 第四步：Decimal 处理（Oracle NUMBER 可能返回 Decimal）
    if isinstance(val, Decimal):
        return float(val)

    return val


def get_oracle_columns(oracle_cursor, table_name):
    """获取 Oracle 表的实际列名列表。"""
    oracle_cursor.execute(
        f"SELECT column_name FROM user_tab_columns WHERE table_name = UPPER(:t) ORDER BY column_id",
        {"t": table_name}
    )
    return [row[0].lower() for row in oracle_cursor.fetchall()]


def get_sqlite_columns(sqlite_cur, table_name):
    """获取 SQLite 表的列名列表。"""
    sqlite_cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in sqlite_cur.fetchall()]


def count_table(oracle_cursor, table_name):
    """获取 Oracle 表的行数。"""
    oracle_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return oracle_cursor.fetchone()[0]


# ============================================================
# 主逻辑
# ============================================================

def migrate():
    # 验证配置
    if not ORACLE_CONFIG["user"] or not ORACLE_CONFIG["dsn"]:
        print("请配置 Oracle 连接信息（环境变量 ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN）")
        print("ORACLE_DSN 格式：host:port/service_name")
        print("示例：192.168.1.100:1521/orcl")
        sys.exit(1)

    print("=" * 60)
    print("Oracle → SQLite 数据迁移")
    print("=" * 60)
    print(f"Oracle DSN:  {ORACLE_CONFIG['dsn']}")
    print(f"SQLite 目标: {SQLITE_DB_PATH}")
    print()

    # 连接 Oracle
    print("[1/5] 连接 Oracle...")
    try:
        oracle_conn = cx_Oracle.connect(
            user=ORACLE_CONFIG["user"],
            password=ORACLE_CONFIG["password"],
            dsn=ORACLE_CONFIG["dsn"],
        )
        oracle_cur = oracle_conn.cursor()
        print("  Oracle 连接成功")
    except Exception as e:
        print(f"  Oracle 连接失败: {e}")
        sys.exit(1)

    # 连接 SQLite
    print("[2/5] 连接 SQLite...")
    sqlite_exists = os.path.exists(SQLITE_DB_PATH)
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.execute("PRAGMA journal_mode=WAL")  # 提高写入性能
    sqlite_conn.execute("PRAGMA foreign_keys=OFF")   # 迁移时关闭外键检查
    sqlite_cur = sqlite_conn.cursor()
    print(f"  SQLite {'已存在' if sqlite_exists else '新建'}: {SQLITE_DB_PATH}")

    # 在 SQLite 中创建表（用 SQLAlchemy 模型定义）
    print("[3/5] 确保 SQLite 表结构存在...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app.db.session import Base
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{os.path.abspath(SQLITE_DB_PATH)}")
        # 只创建不存在的表，不会删除已有的（如 casbin_rule）
        Base.metadata.create_all(bind=engine, checkfirst=True)
        engine.dispose()
        print("  表结构检查完成（已存在的表跳过）")
    except Exception as e:
        print(f"  表结构创建失败: {e}")
        print("  将尝试直接使用已有表继续...")

    # 迁移数据
    print("[4/5] 开始迁移数据...")
    print("-" * 60)
    total_rows = 0

    for table in TABLE_ORDER:
        try:
            # 获取 Oracle 实际列
            oracle_cols = get_oracle_columns(oracle_cur, table)
            if not oracle_cols:
                print(f"  {table}: Oracle 中不存在此表，跳过")
                continue

            # 获取 SQLite 实际列
            sqlite_cols = get_sqlite_columns(sqlite_cur, table)
            if not sqlite_cols:
                print(f"  {table}: SQLite 中不存在此表，跳过")
                continue

            # 找出两边的交集列
            common_cols = [c for c in oracle_cols if c in sqlite_cols]
            # SQLite 中有但 Oracle 中没有的列（后来加的）
            missing_cols = [c for c in sqlite_cols if c not in oracle_cols]

            # Oracle 中不存在的列需要确认（可能是后来加的）
            oracle_missing = MISSING_IN_ORACLE.get(table, [])
            for col in oracle_missing:
                if col in missing_cols:
                    pass  # 已知缺失，正常

            # 行数统计
            row_count = count_table(oracle_cur, table)
            print(f"  {table}: Oracle {row_count} 行, 列 {len(common_cols)}/{len(sqlite_cols)}", end="")

            if row_count == 0:
                print(" → 无数据，跳过")
                continue

            # 清空 SQLite 中该表已有数据（避免重复）
            sqlite_cur.execute(f"DELETE FROM {table}")

            # 从 Oracle 读取数据
            cols_str = ", ".join(common_cols)
            oracle_cur.execute(f"SELECT {cols_str} FROM {table}")

            # 批量插入 SQLite
            placeholders = ", ".join(["?"] * len(sqlite_cols))
            insert_sql = f"INSERT INTO {table} ({', '.join(sqlite_cols)}) VALUES ({placeholders})"
            batch = []
            batch_size = 500

            for row in oracle_cur:
                values = []
                for col in sqlite_cols:
                    if col in common_cols:
                        idx = common_cols.index(col)
                        val = convert_value(row[idx], table, col)
                    else:
                        val = None  # Oracle 中不存在的列填 NULL
                    values.append(val)
                batch.append(tuple(values))

                if len(batch) >= batch_size:
                    sqlite_cur.executemany(insert_sql, batch)
                    batch = []

            if batch:
                sqlite_cur.executemany(insert_sql, batch)

            sqlite_conn.commit()
            total_rows += row_count
            print(f" → 迁移完成")

        except Exception as e:
            print(f" → 失败: {e}")
            sqlite_conn.rollback()
            # 继续下一张表
            continue

    print("-" * 60)
    print(f"  共迁移 {total_rows} 行数据")

    # 更新自增 ID
    print("[5/5] 更新自增 ID 序列...")
    for table in TABLE_ORDER:
        if table in NO_AUTO_INCREMENT:
            continue
        if table not in PK_COLUMNS:
            continue
        pk = PK_COLUMNS[table]
        try:
            sqlite_cur.execute(f"SELECT MAX({pk}) FROM {table}")
            max_id = sqlite_cur.fetchone()[0]
            if max_id:
                sqlite_cur.execute(
                    "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                    (table, max_id)
                )
                print(f"  {table}: MAX(id)={max_id}")
        except Exception as e:
            print(f"  {table}: 跳过 ({e})")

    sqlite_conn.commit()

    # 收尾
    oracle_cur.close()
    oracle_conn.close()
    sqlite_conn.execute("PRAGMA foreign_keys=ON")
    sqlite_conn.close()

    print()
    print("=" * 60)
    print("迁移完成！")
    print(f"SQLite 文件: {os.path.abspath(SQLITE_DB_PATH)}")
    print()
    print("下一步：")
    print("  1. 将 taizhang.db 复制到 backend/ 目录")
    print("  2. 修改后端代码（去掉 Oracle 配置）")
    print("  3. 启动服务验证")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
