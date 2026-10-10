"""
P0.7 迁移: B2 活动申报审批通过后落子表 (PRD §6.2)

变更:
  + portrait_activity_record (B2 落子表):
      id, profile_id (FK), activity_name VARCHAR(200), activity_time DATE,
      activity_type VARCHAR(20), organizer VARCHAR(200),
      award_or_participation VARCHAR(200), content TEXT, hours INTEGER,
      source_submission_id INTEGER,
      created_at, updated_at

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_activity_record.py        # 真迁移 (幂等)
    --dry-run                                         # 只打印计划

设计 (集成指南 §5 雷区 + Rule 12):
  ✅ 幂等: 表已建则 skip, 重复执行无副作用
  ✅ 显式报告 created_tables / skipped_tables / errors 三计数
  ✅ FK 用 CREATE TABLE 显式声明 (SQLite ALTER 不支持加 FK)
  ✅ 失败抛错不吞掉
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return bool(cursor.fetchone())


TABLES_TO_CREATE = [
    (
        "portrait_activity_record",
        """CREATE TABLE portrait_activity_record (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES portrait_profiles(id),
            activity_name VARCHAR(200) NOT NULL,
            activity_time DATE NOT NULL,
            activity_type VARCHAR(20) NOT NULL,
            organizer VARCHAR(200) NOT NULL,
            award_or_participation VARCHAR(200),
            content TEXT,
            hours INTEGER,
            source_submission_id INTEGER,
            created_at DATETIME,
            updated_at DATETIME
        )""",
        "B2 活动申报落子表 (PRD §6.2 v2.1)",
    ),
]


def migrate(db_path: Path, dry_run: bool = False) -> dict:
    result = {
        "created_tables": [],
        "skipped_tables": [],
        "errors": [],
    }

    if not db_path.exists():
        result["errors"].append(f"DB 不存在: {db_path}")
        return result

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if not table_exists(cursor, "portrait_profiles"):
        result["errors"].append(
            "主表 portrait_profiles 不存在, 请先跑 init_db.py"
        )
        conn.close()
        return result

    for table_name, ddl, desc in TABLES_TO_CREATE:
        try:
            if table_exists(cursor, table_name):
                result["skipped_tables"].append(f"{table_name} ({desc})")
                continue

            if not dry_run:
                cursor.execute(ddl)

            result["created_tables"].append(f"{table_name} ({desc})")
            prefix = "[DRY-RUN] " if dry_run else ""
            print(f"  {prefix}+ CREATE TABLE {table_name} ({desc})")
        except Exception as e:
            result["errors"].append(f"{table_name}: {e}")
            print(f"  ❌ {table_name}: {e}", file=sys.stderr)

    if not dry_run:
        conn.commit()
    conn.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="P0.7 B2 活动落子表迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"P0.7 B2 活动落子表迁移 (PRD §6.2):")
    print(f"  - portrait_activity_record")
    print(f"  DB: {args.db_path}")
    print(f"  模式: {'DRY-RUN' if args.dry_run else '真迁移'}")
    print()

    result = migrate(args.db_path, dry_run=args.dry_run)

    print()
    print(f"=== 迁移结果 ===")
    print(f"  新建表: {len(result['created_tables'])}")
    for t in result["created_tables"]:
        print(f"    + {t}")
    print(f"  跳过表 (已存在): {len(result['skipped_tables'])}")
    for t in result["skipped_tables"]:
        print(f"    - {t}")
    print(f"  错误: {len(result['errors'])}")
    for e in result["errors"]:
        print(f"    ❌ {e}")

    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
