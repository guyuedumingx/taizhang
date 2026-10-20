"""Phase 4 迁移: 首次登录标志从画像扩展表归位 users 表 (重构方案)

  1. users 加 is_first_login 列 (BOOLEAN, NULL=未迁移);
  2. 从 portrait_user_metadata.is_first_login 回填存量值;
  3. 回填后画像表的该列保留原值不动 (只读历史, 不再写入)。

幂等: 先查列存在性; 已有非 NULL 值的用户不覆盖。支持 --dry-run。
用法: cd backend && python -m app.db.migrate_first_login_flag [--dry-run]
"""
import argparse
import sys
from sqlalchemy import text

from app.db.session import SessionLocal


def _columns(conn, table: str) -> set:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def migrate(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        conn = db.connection()

        if "is_first_login" not in _columns(conn, "users"):
            stmt = "ALTER TABLE users ADD COLUMN is_first_login BOOLEAN"
            print(f"  [add ] {stmt}")
            if not dry_run:
                conn.execute(text(stmt))
        else:
            print("  [skip] users.is_first_login 已存在")

        if "portrait_user_metadata" in [
            r[0] for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        ]:
            if not dry_run:
                updated = conn.execute(text(
                    "UPDATE users SET is_first_login = ("
                    "  SELECT m.is_first_login FROM portrait_user_metadata m"
                    "  WHERE m.user_id = users.id)"
                    " WHERE is_first_login IS NULL"
                    "   AND EXISTS (SELECT 1 FROM portrait_user_metadata m"
                    "               WHERE m.user_id = users.id)"
                )).rowcount
                print(f"  [fill] 从画像扩展表回填 {updated} 个用户")
        else:
            print("  [skip] portrait_user_metadata 表不存在 (未部署画像), 无需回填")

        if dry_run:
            db.rollback()
            print("\n[DRY-RUN] 未写入")
        else:
            db.commit()
            print("\n完成")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
