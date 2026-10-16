"""
P0.8 迁移: 出入境台账加 seq (序号) 列 (PRD 附录 B.3)

变更:
  + portrait_entry_exit_records.seq INTEGER  (序号, 可空)
    PRD 附录 B.3: "新增'序号'列 (导入时自动生成, 业务表里也可手动填)"
    原代码强制用户填序号, 但 model 无该字段 -> 解析后丢弃

同时落实 PRD 附录 B.3 实施要点:
  - EHR号 列从末尾移至第 2 位 (序号后)
  - 序号 改为可选列, 缺失时按 Excel 行序自动生成

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_entry_exit_seq.py        # 真迁移 (幂等)
    --dry-run                                         # 只打印计划

设计 (集成指南 §5 雷区 + Rule 12):
  ✅ 幂等: 列已存在则 skip, 重复执行无副作用
  ✅ 显式报告 created_columns / skipped_columns / errors 三计数
  ✅ 不动其他列, 仅 ADD COLUMN (SQLite ALTER ADD 幂等性靠列存在性检查)
  ✅ 失败抛错不吞掉
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"

TABLE = "portrait_entry_exit_records"

# 待新增列: (列名, 类型定义, 说明)
COLUMNS_TO_ADD = [
    ("seq", "INTEGER", "序号 (PRD 附录 B.3: 导入时自动生成, 也可手动填)"),
]


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == column for r in cursor.fetchall())


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return bool(cursor.fetchone())


def migrate(db_path: Path, dry_run: bool = False) -> dict:
    result = {"created_columns": [], "skipped_columns": [], "errors": []}

    if not db_path.exists():
        result["errors"].append(f"DB 不存在: {db_path}")
        return result

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if not table_exists(cursor, TABLE):
        result["errors"].append(f"表 {TABLE} 不存在, 请先跑 init_db.py")
        conn.close()
        return result

    for col, coltype, desc in COLUMNS_TO_ADD:
        try:
            if column_exists(cursor, TABLE, col):
                result["skipped_columns"].append(f"{TABLE}.{col} ({desc})")
                continue

            if not dry_run:
                cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN {col} {coltype}")

            result["created_columns"].append(f"{TABLE}.{col} ({desc})")
            prefix = "[DRY-RUN] " if dry_run else ""
            print(f"  {prefix}+ ADD COLUMN {TABLE}.{col} {coltype} ({desc})")
        except Exception as e:
            result["errors"].append(f"{TABLE}.{col}: {e}")
            print(f"  X {TABLE}.{col}: {e}", file=sys.stderr)

    if not dry_run:
        conn.commit()

    # 验证: 打印最终列清单 (Rule 12: 不确认成功就明示)
    cursor.execute(f"PRAGMA table_info({TABLE})")
    cols = [r[1] for r in cursor.fetchall()]
    print(f"\n  {TABLE} 最终列 ({len(cols)}): {cols}")
    conn.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="P0.8 出入境台账加 seq 列 (PRD 附录 B.3)")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"P0.8 出入境 seq 列迁移 (PRD 附录 B.3):")
    print(f"  表: {TABLE}")
    print(f"  新增: seq INTEGER")
    print(f"  DB: {args.db_path}")
    print(f"  模式: {'DRY-RUN' if args.dry_run else '真迁移'}")
    print()

    result = migrate(args.db_path, dry_run=args.dry_run)

    print()
    print(f"=== 迁移结果 ===")
    print(f"  新增列: {len(result['created_columns'])}")
    for c in result["created_columns"]:
        print(f"    + {c}")
    print(f"  跳过列 (已存在): {len(result['skipped_columns'])}")
    for c in result["skipped_columns"]:
        print(f"    - {c}")
    print(f"  错误: {len(result['errors'])}")
    for e in result["errors"]:
        print(f"    X {e}")

    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()