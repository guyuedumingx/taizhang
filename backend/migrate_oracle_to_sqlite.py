"""
Oracle → SQLite 数据迁移脚本

使用方法：
  1. 在下方 CONFIG 区域填写 Oracle 连接信息和 SQLite 目标路径
  2. cd backend/
  3. python migrate_oracle_to_sqlite.py

依赖：pip install cx_Oracle
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from decimal import Decimal

# ============================================================
# CONFIG - 在这里填写连接信息
# ============================================================

ORACLE_HOST = ""           # 例: "192.168.1.100"
ORACLE_PORT = "1521"
ORACLE_SERVICE = ""        # 例: "orcl"
ORACLE_USER = ""
ORACLE_PASSWORD = ""

SQLITE_DB_PATH = "taizhang.db"  # 目标 SQLite 文件路径

# ============================================================
# 以下内容一般不需要修改
# ============================================================

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("migrate")

# 设置 sys.path，确保能导入 app 模块
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# 防止导入 app.core.config 时尝试连接 Oracle
os.environ.setdefault("DATABASE_TYPE", "sqlite")
os.environ.setdefault("ORACLE_USER", "")
os.environ.setdefault("ORACLE_PASSWORD", "")
os.environ.setdefault("ORACLE_SERVICE", "")

# 迁移顺序（按外键依赖拓扑排序）
TABLE_ORDER = [
    "users",
    "teams",
    "roles",
    "workflows",
    "templates",
    "fields",
    "workflow_nodes",
    "workflow_node_approvers",  # 复合主键关联表，无自增 ID
    "ledgers",
    "field_values",
    "workflow_instances",
    "workflow_instance_nodes",
    "system_logs",
    "audit_logs",
    # auto_fill_trigger_configs: Oracle 中不存在此表，跳过
]

# 复合主键表（无自增 ID，不需要更新 sqlite_sequence）
COMPOSITE_PK_TABLES = {"workflow_node_approvers"}

# JSON 列：Oracle 中为 CLOB 存储 JSON 字符串，迁移到 SQLite 时需要 json.loads → json.dumps 标准化
JSON_COLUMNS: dict[str, list[str]] = {
    "ledgers": ["data"],
    "templates": ["default_metadata", "auto_fill_config"],
    "fields": ["options"],
    "workflow_instance_nodes": ["approver_actions"],
    "system_logs": ["details"],
}

# CLOB 但存储纯文本的列（只需 .read() 转字符串，不需要 JSON 处理）
TEXT_LOB_COLUMNS: dict[str, list[str]] = {
    "ledgers": ["description"],
    "teams": ["description"],
    "roles": ["description"],
    "templates": ["description", "default_description"],
    "field_values": ["value"],
    "workflow_nodes": ["description"],
    "workflow_instance_nodes": ["comment"],
    "system_logs": ["message"],
    "audit_logs": ["comment"],
}

BATCH_SIZE = 500


# ============================================================
# 工具函数
# ============================================================

def read_lob(val):
    """读取 Oracle LOB 对象为 Python 字符串"""
    if val is None:
        return None
    if hasattr(val, "read"):
        val = val.read()
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    return val


def convert_value(val, table: str, column: str):
    """
    将 Oracle 单元格值转换为 SQLite 兼容值：
    1. LOB → 字符串
    2. JSON 列 → json.loads + json.dumps 标准化（容错）
    3. datetime → ISO 字符串
    4. Decimal → float
    """
    if val is None:
        return None

    # LOB 处理
    val = read_lob(val)
    if val is None:
        return None

    # 空字符串 → NULL（仅 JSON 列）
    json_cols = JSON_COLUMNS.get(table, [])
    if column in json_cols:
        if not isinstance(val, str) or not val.strip():
            return None
        try:
            return json.dumps(json.loads(val), ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            log.warning("  表 %s 列 %s: 无效 JSON，原样存入 (%.80s...)", table, column, val)
            return val

    # datetime → 标准格式字符串（SQLite 和 SQLAlchemy 都兼容）
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")

    # Oracle NUMBER → Python Decimal → float
    if isinstance(val, Decimal):
        return float(val)

    return val


def get_oracle_columns(cursor, table: str) -> list[str]:
    """获取 Oracle 表的列名列表（保留数据字典中的原始大小写）"""
    cursor.execute(
        "SELECT column_name FROM user_tab_columns WHERE table_name = UPPER(:t) ORDER BY column_id",
        {"t": table},
    )
    return [row[0] for row in cursor.fetchall()]


def get_sqlite_columns(cur, table: str) -> list[str]:
    """获取 SQLite 表的列名列表"""
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


# ============================================================
# 主流程
# ============================================================

def create_sqlite_schema(sqlite_path: str):
    """用 SQLAlchemy Base.metadata 在 SQLite 中创建所有表"""
    from sqlalchemy import create_engine
    from app.db.session import Base

    # 必须导入所有模型，让它们注册到 Base.metadata
    import app.models  # noqa: F401

    engine = create_engine(f"sqlite:///{os.path.abspath(sqlite_path)}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    engine.dispose()
    log.info("SQLite 表结构创建完成: %s", sqlite_path)


def migrate():
    # ---- 校验配置 ----
    if not all([ORACLE_HOST, ORACLE_SERVICE, ORACLE_USER]):
        log.error("请在脚本顶部 CONFIG 区域填写 Oracle 连接信息")
        sys.exit(1)

    log.info("=" * 60)
    log.info("Oracle → SQLite 数据迁移")
    log.info("=" * 60)
    log.info("Oracle: %s:%s/%s  用户: %s", ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE, ORACLE_USER)
    log.info("SQLite: %s", os.path.abspath(SQLITE_DB_PATH))

    # ---- 1. 连接 Oracle ----
    log.info("[1/4] 连接 Oracle ...")
    import cx_Oracle

    try:
        dsn = cx_Oracle.makedsn(ORACLE_HOST, int(ORACLE_PORT), service_name=ORACLE_SERVICE)
        ora_conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
        ora_cur = ora_conn.cursor()
        log.info("  Oracle 连接成功")
    except Exception as e:
        log.error("  Oracle 连接失败: %s", e)
        sys.exit(1)

    # ---- 2. 创建 SQLite 并建表 ----
    log.info("[2/4] 创建 SQLite 表结构 ...")
    try:
        create_sqlite_schema(SQLITE_DB_PATH)
    except Exception as e:
        log.error("  建表失败: %s", e)
        log.error("  请确保在 backend/ 目录下运行，且已安装 sqlalchemy、pydantic-settings")
        ora_cur.close()
        ora_conn.close()
        sys.exit(1)

    sql_conn = sqlite3.connect(SQLITE_DB_PATH)
    sql_conn.execute("PRAGMA journal_mode=WAL")
    sql_conn.execute("PRAGMA foreign_keys=OFF")
    sql_cur = sql_conn.cursor()

    # ---- 3. 迁移数据 ----
    log.info("[3/4] 迁移数据 ...")
    log.info("-" * 60)
    total_rows = 0

    for table in TABLE_ORDER:
        try:
            # 获取 Oracle 列名（原始大小写，如 TYPE、ORDER、LEVEL 等）
            ora_cols_raw = get_oracle_columns(ora_cur, table)
            if not ora_cols_raw:
                log.info("  %-30s Oracle 中不存在，跳过", table)
                continue

            # 构建 小写→原始大小写 的映射
            ora_cols_map: dict[str, str] = {c.lower(): c for c in ora_cols_raw}

            # 获取 SQLite 列名
            sqli_cols = get_sqlite_columns(sql_cur, table)
            if not sqli_cols:
                log.info("  %-30s SQLite 中不存在，跳过", table)
                continue

            # 按SQLite列顺序，构建交集映射：(sqlite_col, oracle_col_original_case)
            # 只迁移两边都有的列
            common: list[tuple[str, str]] = [
                (sc, ora_cols_map[sc.lower()])
                for sc in sqli_cols
                if sc.lower() in ora_cols_map
            ]
            if not common:
                log.info("  %-30s 无交集列，跳过", table)
                continue

            # 行数
            ora_cur.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = ora_cur.fetchone()[0]
            if row_count == 0:
                log.info("  %-30s 0 行，跳过", table)
                continue

            log.info("  %-30s %d 行开始迁移 ...", table, row_count)

            # 清空 SQLite 目标表
            sql_cur.execute(f'DELETE FROM "{table}"')

            # 从 Oracle 读取 —— 对列名加双引号避免保留字冲突（TYPE、ORDER、LEVEL、COMMENT 等）
            ora_select_cols = ", ".join(f'"{ora_col}"' for _, ora_col in common)
            ora_cur.execute(f"SELECT {ora_select_cols} FROM {table}")

            # SQLite INSERT 语句（列名加双引号避免保留字冲突，如 order、type、level 等）
            sqli_cols_quoted = [f'"{c}"' for c in sqli_cols]
            placeholders = ", ".join(["?"] * len(sqli_cols))
            insert_sql = f'INSERT INTO "{table}" ({", ".join(sqli_cols_quoted)}) VALUES ({placeholders})'

            # 构建 SQLite 列 → common 索引的映射
            common_sqlite_set = {sc for sc, _ in common}
            common_idx_map: dict[str, int] = {sc: i for i, (sc, _) in enumerate(common)}

            batch = []
            for row in ora_cur:
                values = []
                for sc in sqli_cols:
                    if sc in common_idx_map:
                        val = convert_value(row[common_idx_map[sc]], table, sc.lower())
                    else:
                        val = None
                    values.append(val)
                batch.append(tuple(values))

                if len(batch) >= BATCH_SIZE:
                    sql_cur.executemany(insert_sql, batch)
                    batch = []

            if batch:
                sql_cur.executemany(insert_sql, batch)

            sql_conn.commit()
            total_rows += row_count
            log.info("  %-30s ✓ 迁移完成", table)

        except Exception as e:
            log.error("  %-30s ✗ 失败: %s", table, e)
            sql_conn.rollback()
            continue

    log.info("-" * 60)
    log.info("共迁移 %d 行", total_rows)

    # ---- 4. 更新自增序列 ----
    # sqlite_sequence 表只有在使用 AUTOINCREMENT 建表时才会自动创建
    # SQLAlchemy 的 create_all 在 SQLite 中使用 INTEGER PRIMARY KEY（不带 AUTOINCREMENT）
    # 所以 sqlite_sequence 可能不存在，但 INTEGER PRIMARY KEY 默认取 max(id)+1，迁移后自增仍然正常
    log.info("[4/4] 检查自增 ID 序列 ...")
    sql_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
    has_seq = sql_cur.fetchone() is not None
    if not has_seq:
        log.info("  sqlite_sequence 不存在（未使用 AUTOINCREMENT），无需手动更新")
        log.info("  SQLite 的 INTEGER PRIMARY KEY 会自动从 max(id)+1 开始分配")
    else:
        for table in TABLE_ORDER:
            if table in COMPOSITE_PK_TABLES:
                continue
            try:
                sql_cur.execute(f"PRAGMA table_info({table})")
                cols = sql_cur.fetchall()
                pk_col = next((c[1] for c in cols if c[5] == 1), None)
                if not pk_col:
                    continue
                sql_cur.execute(f"SELECT MAX({pk_col}) FROM {table}")
                max_id = sql_cur.fetchone()[0]
                if max_id:
                    sql_cur.execute(
                        "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                        (table, max_id),
                    )
                    log.info("  %-30s MAX(id)=%s", table, max_id)
            except Exception as e:
                log.warning("  %-30s 跳过序列更新: %s", table, e)
        sql_conn.commit()

    # ---- 收尾 ----
    ora_cur.close()
    ora_conn.close()
    sql_conn.execute("PRAGMA foreign_keys=ON")
    sql_conn.close()

    log.info("=" * 60)
    log.info("迁移完成！SQLite 文件: %s", os.path.abspath(SQLITE_DB_PATH))
    log.info("=" * 60)


if __name__ == "__main__":
    migrate()
