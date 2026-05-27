"""
为 templates 表添加 auto_fill_config 列的迁移脚本。
SQLite: 执行 ALTER TABLE templates ADD COLUMN auto_fill_config TEXT;
运行方式（在 backend 目录下）: python -m app.db.migrate_auto_fill_config
"""
import os
import sys

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from sqlalchemy import text
from app.db.session import engine


def migrate():
    if settings.DATABASE_TYPE == "sqlite":
        with engine.connect() as conn:
            # SQLite 无 IF NOT EXISTS for ADD COLUMN，先检查列是否存在
            r = conn.execute(text("PRAGMA table_info(templates)"))
            cols = [row[1] for row in r]
            if "auto_fill_config" in cols:
                print("Column auto_fill_config already exists, skip.")
                return
            conn.execute(text("ALTER TABLE templates ADD COLUMN auto_fill_config TEXT"))
            conn.commit()
            print("Added column templates.auto_fill_config (SQLite).")
    else:
        # Oracle 等：可按需添加 ALTER TABLE 语句
        print("Please add column manually: ALTER TABLE templates ADD auto_fill_config CLOB;")


if __name__ == "__main__":
    migrate()
