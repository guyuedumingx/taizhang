"""
P0.1 隐私字段裁剪: 删除 portrait_profiles + portrait_contact_info 8 列
(PRD v2.1 B.6 员工本人信息最小集合)

变更:
  portrait_profiles DROP:
    - id_number         (员工本人身份证号)
    - native_place      (籍贯)
    - birth_place       (出生地)
    - household_place   (户籍地)
  portrait_contact_info DROP:
    - mobile            (员工手机)
    - office_phone      (员工座机)
    - home_phone        (员工家庭电话)
    - home_address      (员工家庭住址)

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_privacy_remove.py            # 真迁移 (会先备份)
    --dry-run                                            # 只打印计划
    --db-path <path>                                     # 自定义 DB 路径

设计 (集成指南 §5 雷区 + Rule 12):
  ✅ 幂等: 列已删则 skip, 重复执行无副作用
  ✅ 备份: 真迁移前自动 cp taizhang.db taizhang.db.bak.{timestamp}
  ✅ SQLite 3.35+ 支持 DROP COLUMN, 老版本会清晰报错
  ✅ 显式报告 deleted / skipped / errors 三计数
  ✅ 失败抛错不吞掉, 整段事务不部分提交
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Windows GBK 默认编码不让打印中文, 强制 UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"

# 待删除列定义: (表名, 列名, 业务原因)
PROFILE_DROPS = [
    ("portrait_profiles", "id_number", "员工本人身份证号"),
    ("portrait_profiles", "native_place", "籍贯"),
    ("portrait_profiles", "birth_place", "出生地"),
    ("portrait_profiles", "household_place", "户籍地"),
]
CONTACT_DROPS = [
    ("portrait_contact_info", "mobile", "员工手机"),
    ("portrait_contact_info", "office_phone", "员工座机"),
    ("portrait_contact_info", "home_phone", "员工家庭电话"),
    ("portrait_contact_info", "home_address", "员工家庭住址"),
]
ALL_DROPS = PROFILE_DROPS + CONTACT_DROPS


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return bool(cursor.fetchone())


def backup_db(db_path: Path) -> Path:
    """迁移前备份 (Rule 12 不可逆操作防御)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.name}.bak.{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def migrate(db_path: Path, dry_run: bool = False) -> dict:
    result = {
        "deleted_columns": [],
        "skipped_columns": [],
        "table_missing": [],
        "errors": [],
    }

    if not db_path.exists():
        result["errors"].append(f"DB 不存在: {db_path}")
        return result

    if not dry_run:
        backup_path = backup_db(db_path)
        print(f"  📦 备份: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # SQLite 版本检查 (DROP COLUMN 需 3.35+)
    sqlite_version = sqlite3.sqlite_version
    version_tuple = tuple(int(x) for x in sqlite_version.split("."))
    if version_tuple < (3, 35, 0):
        result["errors"].append(
            f"SQLite 版本 {sqlite_version} < 3.35, 不支持 DROP COLUMN. 请升级 SQLite."
        )
        conn.close()
        return result

    for table_name, col_name, reason in ALL_DROPS:
        try:
            if not table_exists(cursor, table_name):
                result["table_missing"].append(table_name)
                print(f"  ⚠️ 表 {table_name} 不存在, 跳过 {col_name}")
                continue

            if not column_exists(cursor, table_name, col_name):
                # 幂等: 列已删, skip
                result["skipped_columns"].append(f"{table_name}.{col_name}")
                continue

            sql = f"ALTER TABLE {table_name} DROP COLUMN {col_name}"
            if not dry_run:
                cursor.execute(sql)

            result["deleted_columns"].append(f"{table_name}.{col_name} ({reason})")
            prefix = "[DRY-RUN] " if dry_run else ""
            print(f"  {prefix}- DROP {table_name}.{col_name} ({reason})")
        except Exception as e:
            result["errors"].append(f"{table_name}.{col_name}: {e}")
            print(f"  ❌ {table_name}.{col_name}: {e}", file=sys.stderr)

    if not dry_run:
        conn.commit()
    conn.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="P0.1 隐私字段裁剪迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划, 不修改")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="DB 路径")
    args = parser.parse_args()

    print(f"P0.1 隐私字段裁剪迁移 (PRD v2.1 B.6):")
    print(f"  - portrait_profiles: 4 列 (id_number / native_place / birth_place / household_place)")
    print(f"  - portrait_contact_info: 4 列 (mobile / office_phone / home_phone / home_address)")
    print(f"  DB: {args.db_path}")
    print(f"  模式: {'DRY-RUN' if args.dry_run else '真迁移 (会先备份)'}")
    print()

    result = migrate(args.db_path, dry_run=args.dry_run)

    print()
    print(f"=== 迁移结果 ===")
    print(f"  删除列: {len(result['deleted_columns'])}")
    for c in result["deleted_columns"]:
        print(f"    - {c}")
    print(f"  跳过列 (已删/不存在): {len(result['skipped_columns'])}")
    for c in result["skipped_columns"]:
        print(f"    - {c}")
    if result["table_missing"]:
        print(f"  缺失表: {len(result['table_missing'])}")
        for t in result["table_missing"]:
            print(f"    - {t}")
    print(f"  错误: {len(result['errors'])}")
    for e in result["errors"]:
        print(f"    ❌ {e}")

    if result["errors"]:
        sys.exit(1)

    if result["deleted_columns"] and not args.dry_run:
        print()
        print(f"  💡 提示: ORM 字段需要在 backend/app/portrait/models/profile.py 同步删除")
        print(f"  💡 回滚: cp {args.db_path}.bak.{{timestamp}} {args.db_path}")


if __name__ == "__main__":
    main()
