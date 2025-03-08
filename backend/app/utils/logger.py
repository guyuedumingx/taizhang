import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.log import SystemLog, AuditLog, LogLevel, LogAction
from app.models.workflow import WorkflowInstance, WorkflowInstanceNode

# 配置标准Python日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("taizhang")


class LoggerService:
    """日志服务，用于记录系统日志和审计日志"""
    
    @staticmethod
    def get_client_info(request: Optional[Request] = None) -> Dict[str, Any]:
        """获取客户端信息，包括IP和User-Agent"""
        if not request:
            return {"ip_address": None, "user_agent": None}
        
        # 尝试从X-Forwarded-For获取真实IP，否则使用request.client.host
        ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip_address:
            ip_address = request.client.host if request.client else None
        
        user_agent = request.headers.get("User-Agent")
        
        return {"ip_address": ip_address, "user_agent": user_agent}
    
    @classmethod
    def log_system(
        cls,
        db: Session,
        level: str,
        module: str,
        action: str,
        message: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> SystemLog:
        """记录系统日志"""
        # 获取客户端信息
        client_info = cls.get_client_info(request)
        
        # 创建日志记录
        log_entry = SystemLog(
            user_id=user_id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            level=level,
            module=module,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            message=message,
            details=details,
        )
        
        # 记录到数据库
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        # 同时记录到标准日志
        log_message = f"[{level.upper()}] {module}.{action}: {message}"
        if resource_type and resource_id:
            log_message += f" - {resource_type}:{resource_id}"
        if user_id:
            log_message += f" - User:{user_id}"
        
        if level == LogLevel.INFO:
            logger.info(log_message)
        elif level == LogLevel.WARNING:
            logger.warning(log_message)
        elif level == LogLevel.ERROR:
            logger.error(log_message)
        elif level == LogLevel.DEBUG:
            logger.debug(log_message)
        
        return log_entry
    
    @classmethod
    def log_info(
        cls,
        db: Session,
        module: str,
        action: str,
        message: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> SystemLog:
        """记录信息级别的系统日志"""
        return cls.log_system(
            db=db,
            level=LogLevel.INFO,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )
    
    @classmethod
    def log_warning(
        cls,
        db: Session,
        module: str,
        action: str,
        message: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> SystemLog:
        """记录警告级别的系统日志"""
        return cls.log_system(
            db=db,
            level=LogLevel.WARNING,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )
    
    @classmethod
    def log_error(
        cls,
        db: Session,
        module: str,
        action: str,
        message: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> SystemLog:
        """记录错误级别的系统日志"""
        return cls.log_system(
            db=db,
            level=LogLevel.ERROR,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )
    
    @classmethod
    def log_debug(
        cls,
        db: Session,
        module: str,
        action: str,
        message: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> SystemLog:
        """记录调试级别的系统日志"""
        return cls.log_system(
            db=db,
            level=LogLevel.DEBUG,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )
    
    @classmethod
    def log_audit(
        cls,
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        ledger_id: Optional[int] = None,
        workflow_instance_id: Optional[int] = None,
        status_before: Optional[str] = None,
        status_after: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> AuditLog:
        """记录审计日志"""
        # 创建审计日志记录
        log_entry = AuditLog(
            user_id=user_id,
            ledger_id=ledger_id,
            workflow_instance_id=workflow_instance_id,
            action=action,
            status_before=status_before,
            status_after=status_after,
            comment=comment,
        )
        
        # 记录到数据库
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        # 构造日志消息
        log_message = f"AUDIT: {action}"
        if ledger_id:
            log_message += f" - Ledger:{ledger_id}"
        if workflow_instance_id:
            log_message += f" - WorkflowInstance:{workflow_instance_id}"
        if user_id:
            log_message += f" - User:{user_id}"
        if status_before and status_after:
            log_message += f" - Status:{status_before}->{status_after}"
        if comment:
            log_message += f" - Comment:{comment}"
        
        # 记录到标准日志
        logger.info(log_message)
        
        return log_entry


# 提供全局访问日志服务的快捷方法
def log_info(
    module: str,
    action: str,
    message: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> SystemLog:
    """记录信息级别的系统日志（全局方法）"""
    with SessionLocal() as db:
        return LoggerService.log_info(
            db=db,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )


def log_warning(
    module: str,
    action: str,
    message: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> SystemLog:
    """记录警告级别的系统日志（全局方法）"""
    with SessionLocal() as db:
        return LoggerService.log_warning(
            db=db,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )


def log_error(
    module: str,
    action: str,
    message: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> SystemLog:
    """记录错误级别的系统日志（全局方法）"""
    with SessionLocal() as db:
        return LoggerService.log_error(
            db=db,
            module=module,
            action=action,
            message=message,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
        )


def log_audit(
    action: str,
    user_id: Optional[int] = None,
    ledger_id: Optional[int] = None,
    workflow_instance_id: Optional[int] = None,
    status_before: Optional[str] = None,
    status_after: Optional[str] = None,
    comment: Optional[str] = None,
) -> AuditLog:
    """记录审计日志（全局方法）"""
    with SessionLocal() as db:
        return LoggerService.log_audit(
            db=db,
            action=action,
            user_id=user_id,
            ledger_id=ledger_id,
            workflow_instance_id=workflow_instance_id,
            status_before=status_before,
            status_after=status_after,
            comment=comment,
        ) 