"""
为 portrait_home_visit_records 表添加 scan_status 列的迁移脚本。

背景: PRD 附录 B.4 家访明细表第 14 列「家访记录表扫描件」要求状态值
      已提交 / 未提交, 但模型层此前只有 scan_file_path (文件路径)。
      F11 批量导入按 B.4 的 14 列走, 缺这列模板对不上。

SQLite: ALTER TABLE portrait_home_visit_records ADD COLUMN scan_status VARCHAR(20);
运行方式（在 backend 目录下）: python -m app.db.migrate_home_visit_scan_status
"""
import os
import sys

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from sqlalchemy import text

from app.db.session import engine

TABLE = "portrait_home_visit_records"


def migrate():
    if settings.DATABASE_TYPE == "sqlite":
        with engine.connect() as conn:
            # SQLite 的 ALTER TABLE ADD COLUMN 没有 IF NOT EXISTS, 先查列
            r = conn.execute(text(f"PRAGMA table_info({TABLE})"))
            cols = [row[1] for row in r]
            if "scan_status" in cols:
                print("Column scan_status already exists, skip.")
                return
            conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN scan_status VARCHAR(20)"))
            conn.commit()
            print(f"Added column {TABLE}.scan_status (SQLite).")
    else:
        # Oracle 等：可按需添加 ALTER TABLE 语句
        print(f"Please add column manually: ALTER TABLE {TABLE} ADD scan_status VARCHAR(20);")


if __name__ == "__main__":
    migrate()
