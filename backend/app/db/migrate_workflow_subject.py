"""Phase 2 迁移: WorkflowInstance 主体泛化 + 家访真实绑定列 (重构方案)

为存量库补齐 Phase 2 的 schema 变更:
  1. workflow_instances 加 subject_type / subject_id 两列, 并把存量行
     回填为 subject_type='ledger', subject_id=ledger_id;
  2. 建 (subject_type, subject_id) 唯一索引 (新库由 create_all 建,
     存量 SQLite 用 CREATE UNIQUE INDEX IF NOT EXISTS 补);
  3. portrait_home_visit_records 加 workflow_instance_id 列
     (draft 阶段 NULL, 存量 pending 记录在下次审批动作时由
     workflow_bridge.ensure_submission_instance 同思路补建实例)。

幂等: 全部操作先查存在性; 支持 --dry-run。
用法: cd backend && python -m app.db.migrate_workflow_subject [--dry-run]
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
        added = skipped = 0

        # ---- 1. workflow_instances 主体列 ----
        cols = _columns(conn, "workflow_instances")
        for name, ddl in [
            ("subject_type", "VARCHAR(50) NOT NULL DEFAULT 'ledger'"),
            ("subject_id", "INTEGER"),
        ]:
            if name in cols:
                print(f"  [skip] workflow_instances.{name} 已存在")
                skipped += 1
            else:
                stmt = f"ALTER TABLE workflow_instances ADD COLUMN {name} {ddl}"
                print(f"  [add ] {stmt}")
                if not dry_run:
                    conn.execute(text(stmt))
                added += 1

        # ---- 2. 存量行回填 subject 双键 ----
        if not dry_run:
            updated = conn.execute(text(
                "UPDATE workflow_instances "
                "SET subject_type='ledger', subject_id=ledger_id "
                "WHERE subject_id IS NULL AND ledger_id IS NOT NULL"
            )).rowcount
            print(f"  [fill] 回填存量台账实例 {updated} 行")

        # ---- 3. 唯一索引 (SQLite 允许多个 NULL, 画像实例 ledger_id=NULL 不受旧索引影响) ----
        idx = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_workflow_instance_subject'"
        )).fetchone()
        if idx:
            print("  [skip] 唯一索引 uq_workflow_instance_subject 已存在")
            skipped += 1
        else:
            stmt = ("CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_instance_subject "
                    "ON workflow_instances(subject_type, subject_id)")
            print(f"  [add ] {stmt}")
            if not dry_run:
                conn.execute(text(stmt))
            added += 1

        # ---- 4. 家访绑定列 ----
        cols = _columns(conn, "portrait_home_visit_records")
        if "workflow_instance_id" in cols:
            print("  [skip] portrait_home_visit_records.workflow_instance_id 已存在")
            skipped += 1
        else:
            stmt = ("ALTER TABLE portrait_home_visit_records "
                    "ADD COLUMN workflow_instance_id INTEGER "
                    "REFERENCES workflow_instances(id)")
            print(f"  [add ] {stmt}")
            if not dry_run:
                conn.execute(text(stmt))
            added += 1

        if dry_run:
            db.rollback()
            print(f"\n[DRY-RUN] 将新增 {added} 项, 跳过 {skipped} 项 (未写入)")
        else:
            db.commit()
            print(f"\n完成: 新增 {added} 项, 跳过 {skipped} 项")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    # Windows GBK 兼容 (Rule 12: 错误明细可见)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的变更")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
