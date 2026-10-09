"""
C1 阶段: portrait_home_visit_records 加 3 列迁移 (PRD §7.1 双人员家访 + 扫描件 + 团队名称)

变更:
  + co_visitor_user_id INTEGER  INDEX (FK -> users.id, 双人员家访第二人)
  + scan_file_path VARCHAR(500)            (扫描件相对路径 uploads/portrait/home_visits/{year}/{uuid}.{ext})
  + team_name VARCHAR(100)                (固定 "审核处理团队", 后端兜底写)

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_c1.py            # 真迁移
    --dry-run                                # 只打印计划

设计 (集成指南 §5 雷区 + Rule 12):
  ✅ 幂等: 重复执行不报错 (检查列是否已存在)
  ✅ FK 用 ALTER TABLE SQLite 不支持, 只加列, 外键约束在 ORM 层
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

TABLE_NAME = "portrait_home_visit_records"

COLUMNS_TO_ADD = [
    ("co_visitor_user_id", "INTEGER"),
    ("scan_file_path", "VARCHAR(500)"),
    ("team_name", "VARCHAR(100)"),
]

INDEXES = [
    ("ix_portrait_home_visit_records_co_visitor_user_id", "co_visitor_user_id"),
]


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def index_exists(cursor, table_name: str, index_name: str) -> bool:
    cursor.execute(f"PRAGMA index_list({table_name})")
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
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,)
    )
    if not cursor.fetchone():
        result["errors"].append(f"表 {TABLE_NAME} 不存在, 请先跑 init_db")
        conn.close()
        return result

    for col_name, col_type in COLUMNS_TO_ADD:
        try:
            if column_exists(cursor, TABLE_NAME, col_name):
                result["skipped_columns"].append(col_name)
                continue

            sql = f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col_name} {col_type}"
            if not dry_run:
                cursor.execute(sql)

            result["added_columns"].append(col_name)
            print(f"  {'[DRY-RUN] ' if dry_run else ''}+ ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            result["errors"].append(f"{col_name}: {e}")
            print(f"  ❌ {col_name}: {e}", file=sys.stderr)

    for idx_name, col_name in INDEXES:
        try:
            if index_exists(cursor, TABLE_NAME, idx_name):
                continue
            sql = f"CREATE INDEX {idx_name} ON {TABLE_NAME} ({col_name})"
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
    parser = argparse.ArgumentParser(description=f"C1 {TABLE_NAME} 加 3 列迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"C1 迁移: {TABLE_NAME} 加 3 列 (co_visitor_user_id / scan_file_path / team_name)")
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