from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional

from app.db.session import Base
from sqlalchemy.sql import func

# 日志级别枚举
class LogLevel:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"

# 日志操作类型枚举
class LogAction:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    SUBMIT = "submit"
    CANCEL = "cancel"
    EXPORT = "export"
    IMPORT = "import"

# 系统日志模型
class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    level = Column(String, nullable=False, default=LogLevel.INFO)
    module = Column(String, nullable=False)  # 模块：用户、角色、台账、工作流等
    action = Column(String, nullable=False)  # 操作：创建、更新、删除等
    resource_type = Column(String, nullable=True)  # 资源类型：用户、角色、台账等
    resource_id = Column(String, nullable=True)  # 资源ID
    message = Column(Text, nullable=False)  # 日志消息
    details = Column(JSON, nullable=True)  # 详细信息，JSON格式
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<SystemLog {self.id}: {self.message}>"

# 审计日志模型
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.id"), nullable=True)
    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=True)
    action = Column(String, nullable=False)  # 审核动作：提交、批准、拒绝等
    status_before = Column(String, nullable=True)  # 变更前状态
    status_after = Column(String, nullable=True)  # 变更后状态
    comment = Column(Text, nullable=True)  # 审核意见
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])
    ledger = relationship("Ledger", foreign_keys=[ledger_id])
    workflow_instance = relationship("WorkflowInstance", foreign_keys=[workflow_instance_id])

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action}>" 