"""
台账导入功能数据库迁移脚本

新增字段:
  - imported_by_id   INTEGER  REFERENCES users(id)   实际导入者(老王)
  - import_batch_id  VARCHAR(40)                       导入批次 UUID(索引)

手工创建的台账这两个字段为 NULL。

用法(在项目根目录执行):
    python backend/scripts/migrate_ledger_import_fields.py

数据库类型由 backend/app/core/config.py 的 DATABASE_TYPE 决定:
  - sqlite: 直接执行 ALTER TABLE + CREATE INDEX
  - oracle: 打印手动 SQL 提示(生产 Oracle 需 DBA 执行)
"""
import os
import sys

# 将 backend 目录加入 sys.path,便于直接 import app
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

from sqlalchemy import text  # noqa: E402
from app.db.session import engine, SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402


def _column_exists_sqlite(table: str, column: str) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def _column_exists_oracle(table: str, column: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT COUNT(*) FROM user_tab_columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table.upper(), "c": column.upper()},
        ).fetchone()
    return bool(row and row[0] > 0)


def _index_exists_oracle(index_name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM user_indexes WHERE index_name = :i"),
            {"i": index_name.upper()},
        ).fetchone()
    return bool(row and row[0] > 0)


def migrate_sqlite() -> None:
    print("==> SQLite 模式执行迁移")
    with engine.begin() as conn:
        if not _column_exists_sqlite("ledgers", "imported_by_id"):
            conn.execute(
                text("ALTER TABLE ledgers ADD COLUMN imported_by_id INTEGER REFERENCES users(id)")
            )
            print("    + ledgers.imported_by_id 已添加")
        else:
            print("    = ledgers.imported_by_id 已存在,跳过")

        if not _column_exists_sqlite("ledgers", "import_batch_id"):
            conn.execute(text("ALTER TABLE ledgers ADD COLUMN import_batch_id VARCHAR(40)"))
            print("    + ledgers.import_batch_id 已添加")
        else:
            print("    = ledgers.import_batch_id 已存在,跳过")

        # SQLite 不支持 IF NOT EXISTS 创建索引的 ALTER TABLE,用单独 CREATE INDEX IF NOT EXISTS
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ledgers_import_batch_id "
                "ON ledgers(import_batch_id)"
            )
        )
        print("    + ix_ledgers_import_batch_id 索引已就绪")
    print("==> SQLite 迁移完成")


def migrate_oracle() -> None:
    print("==> Oracle 模式:以下 SQL 需 DBA 手动执行")
    print("    ALTER TABLE ledgers ADD (imported_by_id NUMBER REFERENCES users(id));")
    print("    ALTER TABLE ledgers ADD (import_batch_id VARCHAR2(40));")
    print("    CREATE INDEX ix_ledgers_import_batch_id ON ledgers(import_batch_id);")
    print("==> Oracle 迁移提示已输出")


def main() -> None:
    db_type = settings.DATABASE_TYPE.lower()
    print(f"==> 检测 DATABASE_TYPE={db_type}")
    if db_type == "oracle":
        migrate_oracle()
    else:
        migrate_sqlite()


if __name__ == "__main__":
    main()
