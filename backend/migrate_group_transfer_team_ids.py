"""
一次性迁移: 给 portrait_group_transfer_history 加 from_team_id / to_team_id 两列

为什么需要: 本项目**不用 Alembic** (没有 alembic.ini / versions/), DDL 靠
`Base.metadata.create_all()` —— 而 create_all 只建新表, **不会给已存在的表加列**。
所以模型加了列之后, 必须跑一次这个脚本, 否则运行时直接
`sqlite3.OperationalError: no such column: from_team_id`。

幂等: 已存在的列会跳过, 可重复执行。

用法:
    cd backend && ./venv/Scripts/python.exe migrate_group_transfer_team_ids.py
    ./venv/Scripts/python.exe migrate_group_transfer_team_ids.py --dry-run
"""
import argparse
import os
import sys
from typing import List, Tuple

TABLE = "portrait_group_transfer_history"

# (列名, SQLite DDL 片段)
NEW_COLUMNS: List[Tuple[str, str]] = [
    ("from_team_id", "INTEGER"),
    ("to_team_id", "INTEGER"),
]

# create_all 建的表里这两个列带 FK + index; ALTER TABLE 加的列 SQLite 不支持再补
# 索引, 所以这里只加列。索引对当前数据量 (调换记录很少) 不重要。
# FK 约束在 SQLite 里默认不开 (PRAGMA foreign_keys), 且生产 PG 上 DDL 应由 DBA
# 按部署文档补 —— 这一点写在这里, 不要当成"已经处理好了"。
COLUMN_NOTES = (
    "两列均可为 NULL (未分组/退组)。SQLite 的 ALTER TABLE ADD COLUMN 不支持带 FK 约束,\n"
    "  故脚本不加 FK; 生产 PG/Oracle 部署时请 DBA 补:\n"
    "    ALTER TABLE portrait_group_transfer_history\n"
    "      ADD CONSTRAINT fk_gth_from_team FOREIGN KEY (from_team_id) REFERENCES teams(id),\n"
    "      ADD CONSTRAINT fk_gth_to_team   FOREIGN KEY (to_team_id)   REFERENCES teams(id);\n"
    "  并补索引: CREATE INDEX ix_gth_from_team ON portrait_group_transfer_history(from_team_id);\n"
    "           CREATE INDEX ix_gth_to_team   ON portrait_group_transfer_history(to_team_id);"
)


def existing_columns() -> set:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sqlalchemy import inspect
    from app.db.session import engine

    inspector = inspect(engine)
    if TABLE not in inspector.get_table_names():
        return None  # 表还没建, 直接跑 init_db.py 即可
    return {c["name"] for c in inspector.get_columns(TABLE)}


def run(dry_run: bool) -> Tuple[int, int, List[str]]:
    """Returns: (added, skipped, errors)"""
    from app.db.session import engine

    cols = existing_columns()
    if cols is None:
        return 0, 0, [f"表 {TABLE} 不存在, 请先运行 python init_db.py 建表"]

    added, skipped, errors = 0, 0, []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        for name, ddl in NEW_COLUMNS:
            if name in cols:
                print(f"  [跳过] {name} 已存在")
                skipped += 1
                continue
            print(f"  [{'预演' if dry_run else '执行'}] ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}")
            if dry_run:
                added += 1
                continue
            try:
                cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}")
                raw.commit()
                added += 1
            except Exception as exc:
                errors.append(f"加列 {name} 失败: {type(exc).__name__}: {exc}")
    finally:
        cursor.close()
        raw.close()

    if not dry_run and not errors:
        # 加完列必须让 ORM 的表定义与实际结构一致, 否则 create_all 之后再校验会不一致
        from app.db.session import Base
        import app.models  # noqa: F401
        import app.portrait.models  # noqa: F401
        Base.metadata.create_all(bind=engine)  # 对已存在的表是 no-op
    return added, skipped, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只打印不执行")
    args = parser.parse_args()

    print(f"迁移 {TABLE}: 新增 from_team_id / to_team_id")
    added, skipped, errors = run(dry_run=args.dry_run)

    print("\n--- 结果 ---")
    print(f"新增列: {added}")
    print(f"跳过(已存在): {skipped}")
    print(f"失败: {len(errors)}")
    for msg in errors:
        print(f"  ! {msg}")
    print("\n--- 备注 ---")
    print(COLUMN_NOTES)

    # Rule 12: 有失败就是失败, 退出码非 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())