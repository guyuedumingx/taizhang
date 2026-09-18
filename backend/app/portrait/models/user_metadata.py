"""
数字画像 User 扩展表
=========================

集成指南 §3 阶段 1.1 要求字段重命名。taizhang User 模型已包含 ehr_id/department/
is_active/is_superuser/hashed_password/team_id —— 这些**不需要**在 taizhang 端修改。

但数字画像 User 还有几个 taizhang User 没有的字段:
  - is_first_login (Boolean): 首次登录强制改密
  - deleted_at (DateTime): 软删除时间

按"台账 0 改动"原则, 这两个字段不直接加到 taizhang User, 而是放在本扩展表。
通过 user_id 一对一关联 taizhang users 表。

主键复用 taizhang users.id (1:1)。这种"扩展表"模式:
  ✅ 保持 taizhang 用户表完全不变
  ✅ portrait 业务字段独立维护
  ✅ 删除扩展表不影响 taizhang
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class PortraitUserMetadata(Base):
    """数字画像 User 扩展：is_first_login + soft-delete。

    表名: portrait.user_metadata
    Schema: digital_portrait (P2 阶段启用)
    """
    __tablename__ = "portrait_user_metadata"
    __table_args__ = {"extend_existing": True}

    # 复用 taizhang users.id 作主键（1:1 关联）
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    is_first_login = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # 关系: 反向引用 taizhang User
    user = relationship("User", backref="portrait_metadata")
