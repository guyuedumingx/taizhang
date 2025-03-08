from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta

from app.crud.base import CRUDBase
from app.models.log import SystemLog, AuditLog
from app.schemas.log import SystemLogCreate, AuditLogCreate, LogQueryParams


class CRUDSystemLog(CRUDBase[SystemLog, SystemLogCreate, SystemLogCreate]):
    def get_multi_by_filter(
        self, db: Session, *, params: LogQueryParams
    ) -> List[SystemLog]:
        """按条件查询系统日志"""
        query = db.query(SystemLog)
        
        # 应用过滤条件
        if params.module:
            query = query.filter(SystemLog.module == params.module)
        
        if params.action:
            query = query.filter(SystemLog.action == params.action)
        
        if params.level:
            query = query.filter(SystemLog.level == params.level)
        
        if params.user_id:
            query = query.filter(SystemLog.user_id == params.user_id)
        
        if params.resource_type:
            query = query.filter(SystemLog.resource_type == params.resource_type)
        
        if params.resource_id:
            query = query.filter(SystemLog.resource_id == params.resource_id)
        
        if params.start_date:
            query = query.filter(SystemLog.created_at >= params.start_date)
        
        if params.end_date:
            query = query.filter(SystemLog.created_at <= params.end_date)
        
        # 排序和分页
        query = query.order_by(desc(SystemLog.created_at))
        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        
        return query.all()
    
    def count_by_filter(
        self, db: Session, *, params: LogQueryParams
    ) -> int:
        """按条件统计系统日志数量"""
        query = db.query(SystemLog)
        
        # 应用过滤条件
        if params.module:
            query = query.filter(SystemLog.module == params.module)
        
        if params.action:
            query = query.filter(SystemLog.action == params.action)
        
        if params.level:
            query = query.filter(SystemLog.level == params.level)
        
        if params.user_id:
            query = query.filter(SystemLog.user_id == params.user_id)
        
        if params.resource_type:
            query = query.filter(SystemLog.resource_type == params.resource_type)
        
        if params.resource_id:
            query = query.filter(SystemLog.resource_id == params.resource_id)
        
        if params.start_date:
            query = query.filter(SystemLog.created_at >= params.start_date)
        
        if params.end_date:
            query = query.filter(SystemLog.created_at <= params.end_date)
        
        return query.count()
    
    def get_recent_logs(
        self, db: Session, *, days: int = 7, limit: int = 100
    ) -> List[SystemLog]:
        """获取最近的系统日志"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(SystemLog).filter(
            SystemLog.created_at >= start_date
        ).order_by(desc(SystemLog.created_at)).limit(limit)
        
        return query.all()
    
    def get_errors(
        self, db: Session, *, days: int = 7, limit: int = 100
    ) -> List[SystemLog]:
        """获取最近的错误日志"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(SystemLog).filter(
            SystemLog.created_at >= start_date,
            SystemLog.level == "error"
        ).order_by(desc(SystemLog.created_at)).limit(limit)
        
        return query.all()
    
    def get_by_resource(
        self, db: Session, *, resource_type: str, resource_id: str, limit: int = 100
    ) -> List[SystemLog]:
        """获取指定资源的日志"""
        query = db.query(SystemLog).filter(
            SystemLog.resource_type == resource_type,
            SystemLog.resource_id == resource_id
        ).order_by(desc(SystemLog.created_at)).limit(limit)
        
        return query.all()


class CRUDAuditLog(CRUDBase[AuditLog, AuditLogCreate, AuditLogCreate]):
    def get_by_ledger(
        self, db: Session, *, ledger_id: int, limit: int = 100
    ) -> List[AuditLog]:
        """获取台账的审计日志"""
        query = db.query(AuditLog).filter(
            AuditLog.ledger_id == ledger_id
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        return query.all()
    
    def get_by_workflow_instance(
        self, db: Session, *, workflow_instance_id: int, limit: int = 100
    ) -> List[AuditLog]:
        """获取工作流实例的审计日志"""
        query = db.query(AuditLog).filter(
            AuditLog.workflow_instance_id == workflow_instance_id
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        return query.all()
    
    def get_by_user(
        self, db: Session, *, user_id: int, limit: int = 100
    ) -> List[AuditLog]:
        """获取用户的审计日志"""
        query = db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        return query.all()
    
    def get_recent_approval_logs(
        self, db: Session, *, days: int = 7, limit: int = 100
    ) -> List[AuditLog]:
        """获取最近的审批日志"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(AuditLog).filter(
            AuditLog.created_at >= start_date,
            AuditLog.action.in_(["approve", "reject"])
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        return query.all()


system_log = CRUDSystemLog(SystemLog)
audit_log = CRUDAuditLog(AuditLog) 