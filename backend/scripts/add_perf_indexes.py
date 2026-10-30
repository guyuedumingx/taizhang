"""
性能索引脚本（幂等）：只创建索引，不动任何表结构、不加列、不改数据。

- SQLite（开发库）：直接执行，重复运行自动跳过已存在的索引
- Oracle：
    默认        打印 DDL 清单，由 DBA 在生产执行（建议低峰期，ONLINE 不锁表）
    --execute   在 backend/.env 指向的库上直接执行（开发/测试库用；
                普通 CREATE INDEX，建索引期间会短暂锁 DML，别打在生产上）
    --explain   对每个索引跑一次 EXPLAIN PLAN 并打印执行计划（Oracle 验证用）
    --execute --explain  建完顺带验证

运行（backend 目录下）:
  ./venv/bin/python scripts/add_perf_indexes.py                    # SQLite 执行 / Oracle 打印 DDL
  ./venv/bin/python scripts/add_perf_indexes.py --execute --explain  # Oracle 开发库执行+验证

验证效果:
  sqlite3 taizhang.db "EXPLAIN QUERY PLAN SELECT * FROM ledgers WHERE template_id=5;"
  执行前: SCAN ledgers → 执行后: SEARCH ledgers USING INDEX ix_ledgers_template_id
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

# (索引名, 表, 列) —— 覆盖台账筛选/排序/统计粗筛与字段值双写的高频查询路径
INDEXES = [
    ("ix_ledgers_template_id",    "ledgers",      "template_id"),
    ("ix_ledgers_team_id",        "ledgers",      "team_id"),
    ("ix_ledgers_created_by_id",  "ledgers",      "created_by_id"),
    ("ix_ledgers_created_at",     "ledgers",      "created_at"),
    ("ix_fields_template_id",     "fields",       "template_id"),
    ("ix_field_values_ledger_id", "field_values", "ledger_id"),
    ("ix_field_values_field_id",  "field_values", "field_id"),
]

# 每个索引对应的代表性查询（Oracle EXPLAIN 验证用，值只影响计划形状不影响索引选择）
VERIFY_SQL = {
    "ix_ledgers_template_id":    "SELECT * FROM ledgers WHERE template_id = 1",
    "ix_ledgers_team_id":        "SELECT * FROM ledgers WHERE team_id = 1",
    "ix_ledgers_created_by_id":  "SELECT * FROM ledgers WHERE created_by_id = 1",
    "ix_ledgers_created_at":     "SELECT * FROM ledgers ORDER BY created_at DESC",
    "ix_fields_template_id":     "SELECT * FROM fields WHERE template_id = 1",
    "ix_field_values_ledger_id": "SELECT * FROM field_values WHERE ledger_id = 1",
    "ix_field_values_field_id":  "SELECT * FROM field_values WHERE field_id = 1",
}


def migrate_sqlite():
    with engine.connect() as conn:
        existing = {
            row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
        }
        created = skipped = 0
        for name, table, col in INDEXES:
            if name in existing:
                print(f"  = {name} 已存在，跳过")
                skipped += 1
                continue
            conn.execute(text(f"CREATE INDEX {name} ON {table} ({col})"))
            print(f"  + {name} ON {table}({col}) 创建成功")
            created += 1
        conn.commit()
    print(f"完成：新建 {created} 个，跳过 {skipped} 个")


def print_oracle_ddl():
    print("Oracle 生产环境请由 DBA 在低峰期执行（不锁表、不产生 redo 放大）：")
    for name, table, col in INDEXES:
        print(f"  CREATE INDEX {name} ON {table} ({col}) NOLOGGING ONLINE;")


def execute_oracle():
    """在 .env 指向的 Oracle 上直接建索引（幂等，按 USER_INDEXES 判断）。"""
    print(f"目标库: {settings.ORACLE_USER}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}"
          f"/?service_name={settings.ORACLE_SERVICE}")
    if settings.ORACLE_PASSWORD == "CHANGE_ME":
        print("✗ backend/.env 里 ORACLE_PASSWORD 还是占位值 CHANGE_ME，先填真实连接参数")
        sys.exit(2)
    with engine.connect() as conn:
        existing = {
            row[0].lower() for row in conn.execute(text("SELECT index_name FROM user_indexes"))
        }
        created = skipped = 0
        for name, table, col in INDEXES:
            if name.lower() in existing:
                print(f"  = {name} 已存在，跳过")
                skipped += 1
                continue
            # 开发库用普通 CREATE INDEX（ONLINE 是企业版权限，普通版更稳）
            conn.execute(text(f"CREATE INDEX {name} ON {table} ({col})"))
            conn.commit()
            print(f"  + {name} ON {table}({col}) 创建成功")
            created += 1
    print(f"完成：新建 {created} 个，跳过 {skipped} 个")


def explain_oracle():
    """EXPLAIN PLAN 逐索引验证：计划里出现索引名 = 生效，TABLE ACCESS FULL = 未走索引。"""
    print("\n—— EXPLAIN PLAN 验证 ——")
    ok = miss = 0
    with engine.connect() as conn:
        for name, sql in ((n, VERIFY_SQL[n]) for n, _, _ in INDEXES):
            conn.execute(text(f"EXPLAIN PLAN FOR {sql}"))
            rows = conn.execute(
                text("SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC'))")
            ).fetchall()
            plan = "\n".join((r[0] or "").rstrip() for r in rows)
            if name.upper() in plan.upper():
                ok += 1
                print(f"  ✓ {name} 被使用")
            else:
                miss += 1
                print(f"  ⚠ {name} 未出现在计划中（可能是小表优化器选了全表扫描，属正常；")
                print(f"    也可能统计信息过期，可先 EXEC DBMS_STATS.GATHER_TABLE_STATS）")
            print(f"{'-' * 60}\n{plan}\n{'-' * 60}")
    print(f"验证汇总：走索引 {ok} 个，未走 {miss} 个（未走≠索引无效，见上方说明）")


def migrate():
    args = sys.argv[1:]
    if settings.DATABASE_TYPE == "sqlite":
        print(f"SQLite ({settings.SQLITE_DATABASE_URI}):")
        migrate_sqlite()
        return
    if "--execute" in args:
        execute_oracle()
        if "--explain" in args:
            explain_oracle()
    else:
        print_oracle_ddl()
        if "--explain" in args:
            explain_oracle()


if __name__ == "__main__":
    migrate()
