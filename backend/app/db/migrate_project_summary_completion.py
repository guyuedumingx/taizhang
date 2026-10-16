"""
为 portrait_project_summary 表添加 3 列的迁移脚本。

背景 (2026-10-16 决策 3): B1 专项工作审批通过后改为落 portrait_project_summary
      (画像自有表), 不再写台账 ledgers —— 画像将来单独部署时台账表不存在。
      落点字段由业务方给定: 用户名 / 时间 / 专项名称 / 专项内容 / 完成情况。
      前 4 项现有列已够, 本脚本补:
        completion_status    VARCHAR(50)  完成情况
        source_submission_id INTEGER      来源 submission (可追溯 + 防重复落表)
        hours                VARCHAR(50)  预估工时 (B1 表单收集, 决策 3 未列但不丢数据)

SQLite: ALTER TABLE 不支持 IF NOT EXISTS, 需逐列 PRAGMA 检查后添加。
运行方式（在 backend 目录下）: python -m app.db.migrate_project_summary_completion
"""
import os
import sys

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from sqlalchemy import text

from app.db.session import engine

TABLE = "portrait_project_summary"

# (列名, 完整列定义) —— 顺序即添加顺序
NEW_COLUMNS = [
    ("completion_status", "VARCHAR(50)"),
    ("hours", "INTEGER"),
    ("source_submission_id", "INTEGER"),
]


def migrate():
    if settings.DATABASE_TYPE != "sqlite":
        # Oracle 等：可按需添加 ALTER TABLE 语句
        print(f"Please add columns manually on {TABLE}:")
        for name, ddl in NEW_COLUMNS:
            print(f"  ALTER TABLE {TABLE} ADD {name} {ddl};")
        return

    added, skipped = [], []
    with engine.connect() as conn:
        r = conn.execute(text(f"PRAGMA table_info({TABLE})"))
        existing = [row[1] for row in r]

        # 表不存在时显性报错, 不静默通过 (Rule 12)
        if not existing:
            raise SystemExit(
                f"表 {TABLE} 不存在。画像单独部署的新库请用 Base.metadata.create_all 建表, "
                f"本脚本只负责给已有库补列。"
            )

        for name, ddl in NEW_COLUMNS:
            if name in existing:
                skipped.append(name)
                continue
            conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}"))
            added.append(name)
        conn.commit()

    # 跳过数量和原因必须在输出里展示, 不能埋在日志里 (Rule 12)
    print(f"{TABLE}: 新增 {len(added)} 列 -> {added}")
    if skipped:
        print(f"{TABLE}: 已存在跳过 {len(skipped)} 列 -> {skipped}")

    # 单列索引: source_submission_id 供幂等查询用
    with engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_source_submission_id "
                f"ON {TABLE} (source_submission_id)"
            )
        )
        conn.commit()
    print(f"索引 ix_{TABLE}_source_submission_id 已就绪")


if __name__ == "__main__":
    migrate()
