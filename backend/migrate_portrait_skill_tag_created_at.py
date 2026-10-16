"""
迁移: 回填 portrait_profile_skill_tags.created_at 的 NULL

背景:
  表结构 created_at DATETIME 无 NOT NULL 约束, 而 ProfileSkillTag schema 曾声明
  created_at: datetime (必填), 导致任何 created_at 为 NULL 的历史行会让
  GET /portrait/profiles/me 抛 ValidationError -> 整个 A1 个人档案页 500。

本脚本把存量 NULL 回填为当前时间 (不猜原始值), 并报告处理条数。
schema 同时已改为 Optional[datetime], 双保险: 即使将来再出现 NULL 也不会 500。

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_skill_tag_created_at.py --dry-run   # 只打印
    python migrate_portrait_skill_tag_created_at.py             # 真回填

幂等: 只处理 created_at IS NULL 的行, 重复执行无副作用 (Rule 12: 显式报告)
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "taizhang.db"
TABLE = "portrait_profile_skill_tags"


def run(db_path: Path, dry_run: bool) -> dict:
    result = {"backfilled": 0, "skipped": 0, "errors": []}
    if not db_path.exists():
        result["errors"].append(f"DB 不存在: {db_path}")
        return result

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if not cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)
    ).fetchone():
        result["errors"].append(f"表 {TABLE} 不存在")
        conn.close()
        return result

    nulls = cur.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE created_at IS NULL").fetchone()[0]
    total = cur.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    result["skipped"] = total - nulls

    print(f"  表 {TABLE}: 共 {total} 行, created_at IS NULL: {nulls} 行")

    if nulls == 0:
        print("  无需回填")
        conn.close()
        return result

    if dry_run:
        print(f"  [DRY-RUN] 将把 {nulls} 行的 created_at 回填为当前时间")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cur.execute(
                f"UPDATE {TABLE} SET created_at = ? WHERE created_at IS NULL", (now,)
            )
            conn.commit()
            result["backfilled"] = cur.rowcount
            print(f"  + 已回填 {cur.rowcount} 行, created_at = {now}")
        except Exception as e:
            conn.rollback()
            result["errors"].append(f"回填失败: {e}")
            print(f"  X 回填失败: {e}", file=sys.stderr)

    left = cur.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE created_at IS NULL").fetchone()[0]
    print(f"  回填后残留 NULL: {left}")
    if not dry_run and left != 0:
        result["errors"].append(f"仍有 {left} 行 created_at 为 NULL")
    conn.close()
    return result


def main():
    p = argparse.ArgumentParser(description="回填技能标签 created_at 的 NULL")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--db-path", type=Path, default=DB_PATH)
    args = p.parse_args()

    print(f"回填 {TABLE}.created_at")
    print(f"  DB: {args.db_path}")
    print(f"  模式: {'DRY-RUN' if args.dry_run else '真回填'}\n")

    r = run(args.db_path, args.dry_run)

    print(f"\n=== 结果 ===")
    print(f"  回填行数: {r['backfilled']}")
    print(f"  未动行数: {r['skipped']}")
    print(f"  错误    : {len(r['errors'])}")
    for e in r["errors"]:
        print(f"    X {e}")
    if r["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()