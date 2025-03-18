from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app import crud, models, schemas

class LogService:
    @staticmethod
    def get_system_logs(db: Session, params: schemas.LogQueryParams) -> List[models.SystemLog]:
        """
        获取系统日志列表
        """
        return crud.system_log.get_multi_by_filter(db, params=params)

    @staticmethod
    def count_system_logs(db: Session, params: schemas.LogQueryParams) -> int:
        """
        统计系统日志数量
        """
        return crud.system_log.count_by_filter(db, params=params)

    @staticmethod
    def get_recent_system_logs(db: Session, days: int, limit: int) -> List[models.SystemLog]:
        """
        获取最近的系统日志
        """
        return crud.system_log.get_recent_logs(db, days=days, limit=limit)

    @staticmethod
    def get_error_logs(db: Session, days: int, limit: int) -> List[models.SystemLog]:
        """
        获取错误日志
        """
        return crud.system_log.get_errors(db, days=days, limit=limit)

    @staticmethod
    def get_resource_logs(
        db: Session, 
        resource_type: str, 
        resource_id: str, 
        limit: int
    ) -> List[models.SystemLog]:
        """
        获取指定资源的日志
        """
        return crud.system_log.get_by_resource(
            db, resource_type=resource_type, resource_id=resource_id, limit=limit
        )

    @staticmethod
    def get_audit_logs(
        db: Session,
        ledger_id: Optional[int] = None,
        workflow_instance_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[models.AuditLog]:
        """
        获取审计日志
        """
        if ledger_id:
            return crud.audit_log.get_by_ledger(db, ledger_id=ledger_id, limit=limit)
        elif workflow_instance_id:
            return crud.audit_log.get_by_workflow_instance(
                db, workflow_instance_id=workflow_instance_id, limit=limit
            )
        elif user_id:
            return crud.audit_log.get_by_user(db, user_id=user_id, limit=limit)
        else:
            # 获取最近的审批日志
            return crud.audit_log.get_recent_approval_logs(db, days=7, limit=limit)

    @staticmethod
    def get_ledger_audit_logs(db: Session, ledger_id: int, limit: int) -> List[models.AuditLog]:
        """
        获取特定台账的审计日志
        """
        # 检查台账是否存在
        ledger = crud.ledger.get(db, id=ledger_id)
        if not ledger:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="台账不存在"
            )
        
        return crud.audit_log.get_by_ledger(db, ledger_id=ledger_id, limit=limit)

    @staticmethod
    def get_workflow_audit_logs(db: Session, workflow_id: int, limit: int) -> List[models.AuditLog]:
        """
        获取特定工作流的审计日志
        """
        # 检查工作流是否存在
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="工作流不存在"
            )
        
        # 获取工作流关联的所有工作流实例
        workflow_instances = db.query(models.WorkflowInstance).filter(
            models.WorkflowInstance.workflow_id == workflow_id
        ).all()
        
        if not workflow_instances:
            return []
        
        # 获取这些工作流实例的审计日志
        instance_ids = [instance.id for instance in workflow_instances]
        return db.query(models.AuditLog).filter(
            models.AuditLog.workflow_instance_id.in_(instance_ids)
        ).order_by(
            models.AuditLog.created_at.desc()
        ).limit(limit).all()

    @staticmethod
    def get_user_audit_logs(db: Session, user_id: int, limit: int) -> List[models.AuditLog]:
        """
        获取特定用户的审计日志
        """
        # 检查用户是否存在
        user = crud.user.get(db, id=user_id)
        if not user:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )
        
        return crud.audit_log.get_by_user(db, user_id=user_id, limit=limit)


log_service = LogService() 