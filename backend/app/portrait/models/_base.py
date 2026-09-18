"""
portrait 模型共享基类

集成指南 §1 思路 A: portrait 业务表独立存储
- 实现: 表名前缀 `portrait_` (开发 SQLite / 生产 PG/Oracle 都一致)
- 生产 PG/Oracle: 部署时由 DBA 在 digital_portrait schema 里建 portrait_xxx 表
- 为什么不直接用 schema="digital_portrait" 参数:
  - SQLAlchemy 2.0 + SQLite 不能 resolve 跨 schema FK
  - SQLAlchemy 1.4 在 SQLite 下行为不稳定 (忽略 schema 但 FK 路径仍按 schema 解析)
  - 表名前缀是更稳的方案, 不依赖运行时 schema 处理
"""
from datetime import datetime, timedelta, timezone

# 独立 schema 标识 (部署文档引用, 不在 ORM 里使用)
PORTRAIT_SCHEMA = "digital_portrait"

# 表名前缀常量
PORTRAIT_PREFIX = "portrait_"

# 北京时间统一时区 (Rule 11: 沿用数字画像原约定)
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回北京时间的当前时间 (无时区)"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


# 通用表参数: 不带 schema (开发/生产一致, 靠表名前缀隔离)
PORTRAIT_TABLE_KWARGS: dict = {}