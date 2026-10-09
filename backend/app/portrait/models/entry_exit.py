"""
portrait 出入境台账模型 (PRD §10.1 F5-F9)
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.session import Base

from app.portrait.models._base import PORTRAIT_TABLE_KWARGS, beijing_now


class EntryExitRecord(Base):
    """出入境台账 - 管理员维护, 员工只读自己的

    表名: portrait_entry_exit_records
    """
    __tablename__ = "portrait_entry_exit_records"
    __table_args__ = PORTRAIT_TABLE_KWARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ehr_id = Column(String(7), nullable=False, index=True)  # 冗余, 方便查询/导出

    # 17 列 (PRD §10.1.2)
    name = Column(String(64), nullable=False)          # 姓名
    team_name = Column(String(128), nullable=False)    # 团队
    position = Column(String(64), nullable=False)      # 职务
    certificate_no = Column(String(64), nullable=False)  # 证照号
    outbound_reason = Column(Text, nullable=False)     # 出境原因
    destination = Column(String(128), nullable=False)  # 目的地
    apply_depart_at = Column(DateTime, nullable=False)  # 申请离境
    apply_return_at = Column(DateTime, nullable=False)  # 申请返回
    certificate_type = Column(String(32), nullable=False)  # 证照类别
    apply_type = Column(String(32), nullable=False)    # 申请类型
    team_approver = Column(String(64), nullable=False)  # 团队审批人
    actual_depart_at = Column(DateTime, nullable=True)  # 实际出境
    actual_return_at = Column(DateTime, nullable=True)  # 实际返回
    year = Column(Integer, nullable=False, index=True)  # 年份 (高亮字段)
    group_name = Column(String(128), nullable=True)     # 组别
    remark = Column(Text, nullable=True)                # 备注

    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)