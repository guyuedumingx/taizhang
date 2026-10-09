"""
P0.2 新建子表迁移: portrait_interest_info + portrait_award_info
(PRD §5.4 兴趣爱好 + §5.5 获奖信息)

变更:
  + portrait_interest_info (A4 兴趣):
      id, profile_id (FK), interest_name VARCHAR(100), proficiency VARCHAR(20),
      created_at, updated_at
  + portrait_award_info (A5 获奖):
      id, profile_id (FK), award_name VARCHAR(200), awarding_organization VARCHAR(200),
      award_time DATE, level VARCHAR(20),
      created_at, updated_at

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_v21_subtables.py        # 真迁移 (幂等)
    --dry-run                                       # 只打印计划

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

# Windows GBK 默认编码不让打印中文, 强制 UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return bool(cursor.fetchone())


# 建表 SQL (与 ORM models/profile.py 字段保持一致, Rule 8 先读再写)
TABLES_TO_CREATE = [
    (
        "portrait_interest_info",
        """CREATE TABLE portrait_interest_info (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES portrait_profiles(id),
            interest_name VARCHAR(100) NOT NULL,
            proficiency VARCHAR(20) NOT NULL DEFAULT '入门',
            created_at DATETIME,
            updated_at DATETIME
        )""",
        "A4 兴趣爱好 (PRD §5.4)",
    ),
    (
        "portrait_award_info",
        """CREATE TABLE portrait_award_info (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES portrait_profiles(id),
            award_name VARCHAR(200) NOT NULL,
            awarding_organization VARCHAR(200),
            award_time DATE,
            level VARCHAR(20),
            created_at DATETIME,
            updated_at DATETIME
        )""",
        "A5 获奖信息 (PRD §5.5)",
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

    # 校验 portrait_profiles 主表存在 (否则 FK 会失败)
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
    parser = argparse.ArgumentParser(description="P0.2 portrait 新建 2 张子表迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"P0.2 新建子表迁移 (PRD §5.4 + §5.5):")
    print(f"  - portrait_interest_info (A4 兴趣)")
    print(f"  - portrait_award_info (A5 获奖)")
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
