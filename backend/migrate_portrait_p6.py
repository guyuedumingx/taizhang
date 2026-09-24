"""
P6 阶段: portrait_home_visit_records 加 4 列审批字段迁移

变更:
  + status            VARCHAR(20)  DEFAULT 'draft'  INDEX
  + current_approver_id INTEGER FK users(id)
  + submitted_at      DATETIME
  + completed_at      DATETIME

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_p6.py            # 真迁移
    --dry-run                                # 只打印计划

设计 (集成指南 §5 雷区 + Rule 12):
  ✅ 幂等: 重复执行不报错 (检查列是否已存在)
  ✅ 旧 status 用 default='draft' 补齐 (已有数据视为草稿)
  ✅ 失败抛错不吞掉
  ✅ 显式报告 applied / skipped / errors 计数
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Windows GBK 默认编码不让打印 ❌, 强制 UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"

COLUMNS_TO_ADD = [
    ("status", "VARCHAR(20) DEFAULT 'draft' NOT NULL"),
    ("current_approver_id", "INTEGER"),
    ("submitted_at", "DATETIME"),
    ("completed_at", "DATETIME"),
]
INDEXES = [
    ("ix_portrait_home_visit_records_status", "status"),
]


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def index_exists(cursor, index_name: str) -> bool:
    cursor.execute("PRAGMA index_list(portrait_home_visit_records)")
    return any(row[1] == index_name for row in cursor.fetchall())


def migrate(db_path: Path, dry_run: bool = False) -> dict:
    result = {"added_columns": [], "skipped_columns": [], "added_indexes": [], "errors": []}

    if not db_path.exists():
        result["errors"].append(f"DB 不存在: {db_path}")
        return result

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='portrait_home_visit_records'"
    )
    if not cursor.fetchone():
        result["errors"].append("表 portrait_home_visit_records 不存在, 请先跑 init_db")
        conn.close()
        return result

    for col_name, col_type in COLUMNS_TO_ADD:
        try:
            if column_exists(cursor, "portrait_home_visit_records", col_name):
                result["skipped_columns"].append(col_name)
                continue

            sql = f"ALTER TABLE portrait_home_visit_records ADD COLUMN {col_name} {col_type}"
            if not dry_run:
                cursor.execute(sql)

            result["added_columns"].append(col_name)
            print(f"  {'[DRY-RUN] ' if dry_run else ''}+ ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            result["errors"].append(f"{col_name}: {e}")
            print(f"  ❌ {col_name}: {e}", file=sys.stderr)

    for idx_name, col_name in INDEXES:
        try:
            if index_exists(cursor, idx_name):
                continue
            sql = f"CREATE INDEX {idx_name} ON portrait_home_visit_records ({col_name})"
            if not dry_run:
                cursor.execute(sql)
            result["added_indexes"].append(idx_name)
            print(f"  {'[DRY-RUN] ' if dry_run else ''}+ CREATE INDEX {idx_name}")
        except Exception as e:
            result["errors"].append(f"{idx_name}: {e}")
            print(f"  ❌ {idx_name}: {e}", file=sys.stderr)

    if not dry_run:
        conn.commit()
    conn.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="P6 portrait_home_visit_records 加 4 列迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"P6 迁移: portrait_home_visit_records 加 4 列审批字段")
    print(f"  DB: {args.db_path}")
    print(f"  模式: {'DRY-RUN' if args.dry_run else '真迁移'}")
    print()

    result = migrate(args.db_path, dry_run=args.dry_run)

    print()
    print(f"=== 迁移结果 ===")
    print(f"  新增列: {len(result['added_columns'])} -> {result['added_columns']}")
    print(f"  跳过列: {len(result['skipped_columns'])} -> {result['skipped_columns']}")
    print(f"  新增索引: {len(result['added_indexes'])} -> {result['added_indexes']}")
    print(f"  错误: {len(result['errors'])} -> {result['errors']}")

    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()