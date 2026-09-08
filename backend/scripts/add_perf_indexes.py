"""
性能索引脚本（幂等）：只创建索引，不动任何表结构、不加列、不改数据。

- SQLite（开发库）：直接执行，重复运行自动跳过已存在的索引
- Oracle（生产）：打印 DDL 清单，由 DBA 执行（建议低峰期， ONLINE 不锁表）

运行（backend 目录下）: ./venv/bin/python scripts/add_perf_indexes.py
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


def migrate():
    if settings.DATABASE_TYPE == "sqlite":
        print(f"SQLite ({settings.SQLITE_DATABASE_URI}):")
        migrate_sqlite()
    else:
        print_oracle_ddl()


if __name__ == "__main__":
    migrate()
