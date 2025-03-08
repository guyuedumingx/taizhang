from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService, log_audit

router = APIRouter()


@router.get("/tasks", response_model=List[Dict[str, Any]])
def get_pending_tasks(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的待办任务列表
    """
    # 获取用户的待办任务
    tasks = crud.workflow_instance_node.get_user_pending_tasks(db, user_id=current_user.id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="list_tasks",
        message="获取待办任务列表",
        user_id=current_user.id,
    )
    
    return tasks


@router.get("/ledgers", response_model=List[schemas.Ledger])
def get_approval_ledgers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取需要审批的台账列表
    """
    # 检查权限
    if not deps.check_permissions("ledger", "approve", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 构建查询
    query = db.query(models.Ledger).filter(
        models.Ledger.current_approver_id == current_user.id
    )
    
    if status:
        query = query.filter(models.Ledger.approval_status == status)
    
    ledgers = query.offset(skip).limit(limit).all()
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="list_ledgers",
        message="获取待审批台账列表",
        user_id=current_user.id,
    )
    
    return ledgers


@router.post("/ledgers/{ledger_id}/submit", response_model=schemas.Ledger)
def submit_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    submit_data: schemas.LedgerSubmit,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    提交台账进入审批流程
    """
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查是否为台账创建者或有编辑权限
    if ledger.created_by_id != current_user.id and not deps.check_permissions("ledger", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账状态
    if ledger.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态的台账可以提交审批")
    
    # 检查是否已经有活动的工作流实例
    active_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if active_instance:
        raise HTTPException(status_code=400, detail="台账已经在审批流程中")
    
    # 获取工作流ID
    workflow_id = submit_data.workflow_id
    if not workflow_id:
        # 如果没有指定工作流，使用模板默认工作流
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        if not template or not template.default_workflow_id:
            raise HTTPException(status_code=400, detail="未指定工作流且模板没有默认工作流")
        workflow_id = template.default_workflow_id
    
    # 检查工作流是否存在且激活
    workflow = db.query(models.Workflow).filter(
        models.Workflow.id == workflow_id,
        models.Workflow.is_active == True
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=400, detail="工作流不存在或未激活")
    
    # 创建工作流实例
    workflow_instance = crud.workflow_instance.create_with_nodes(
        db=db,
        workflow_id=workflow_id,
        ledger_id=ledger_id,
        created_by=current_user.id
    )
    
    if not workflow_instance:
        raise HTTPException(status_code=500, detail="创建工作流实例失败")
    
    # 获取第一个节点和审批人
    first_node = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.id == workflow_instance.current_node_id
    ).first()
    
    # 更新台账状态
    ledger_update = {
        "status": "active",
        "approval_status": "pending",
        "submitted_at": datetime.now(),
        "workflow_id": workflow_id,
    }
    
    if first_node and first_node.approver_id:
        ledger_update["current_approver_id"] = first_node.approver_id
    
    ledger = crud.ledger.update(db, db_obj=ledger, obj_in=ledger_update)
    
    # 记录审计日志
    log_audit(
        action="submit",
        user_id=current_user.id,
        ledger_id=ledger_id,
        workflow_instance_id=workflow_instance.id,
        status_before="draft",
        status_after="pending",
    )
    
    # 记录系统日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="submit",
        message=f"提交台账 {ledger.name} 进入审批流程",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger_id),
    )
    
    return ledger


@router.post("/ledgers/{ledger_id}/approve", response_model=schemas.Ledger)
def approve_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    approval_data: schemas.LedgerApproval,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    审批台账
    """
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查是否为当前审批人
    if ledger.current_approver_id != current_user.id and not deps.check_permissions("ledger", "admin_approve", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账状态
    if ledger.approval_status != "pending":
        raise HTTPException(status_code=400, detail="台账当前不在待审批状态")
    
    # 获取活动的工作流实例
    workflow_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if not workflow_instance:
        raise HTTPException(status_code=400, detail="没有找到活动的审批流程")
    
    # 审批操作
    if approval_data.action == "approve":
        # 审批通过
        result = crud.workflow_instance.approve_current_node(
            db=db,
            instance_id=workflow_instance.id,
            user_id=current_user.id,
            comment=approval_data.comment,
            next_approver_id=approval_data.next_approver_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 更新台账状态
        ledger_update = {}
        
        if result.get("workflow_completed", False):
            # 工作流完成，台账审批通过
            ledger_update["approval_status"] = "approved"
            ledger_update["status"] = "completed"
            ledger_update["approved_at"] = datetime.now()
            ledger_update["current_approver_id"] = None
            
            # 记录审计日志 - 最终审批通过
            log_audit(
                action="final_approve",
                user_id=current_user.id,
                ledger_id=ledger_id,
                workflow_instance_id=workflow_instance.id,
                status_before="pending",
                status_after="approved",
                comment=approval_data.comment
            )
        else:
            # 获取下一个节点的审批人
            next_instance_node = db.query(models.WorkflowInstanceNode).filter(
                models.WorkflowInstanceNode.id == result["next_node_id"]
            ).first()
            
            if next_instance_node and next_instance_node.approver_id:
                ledger_update["current_approver_id"] = next_instance_node.approver_id
            
            # 记录审计日志 - 审批通过，流转到下一节点
            log_audit(
                action="approve",
                user_id=current_user.id,
                ledger_id=ledger_id,
                workflow_instance_id=workflow_instance.id,
                status_before="pending",
                status_after="pending",
                comment=approval_data.comment
            )
        
        # 更新台账
        if ledger_update:
            ledger = crud.ledger.update(db, db_obj=ledger, obj_in=ledger_update)
    
    elif approval_data.action == "reject":
        # 拒绝审批
        result = crud.workflow_instance.reject_current_node(
            db=db,
            instance_id=workflow_instance.id,
            user_id=current_user.id,
            comment=approval_data.comment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 更新台账状态
        ledger_update = {}
        
        if result.get("workflow_completed", False):
            # 工作流结束，台账审批被拒绝
            ledger_update["approval_status"] = "rejected"
            ledger_update["status"] = "draft"  # 退回草稿状态
            ledger_update["current_approver_id"] = None
            
            # 记录审计日志 - 最终拒绝
            log_audit(
                action="final_reject",
                user_id=current_user.id,
                ledger_id=ledger_id,
                workflow_instance_id=workflow_instance.id,
                status_before="pending",
                status_after="rejected",
                comment=approval_data.comment
            )
        else:
            # 获取回退后的节点的审批人
            next_instance_node = db.query(models.WorkflowInstanceNode).filter(
                models.WorkflowInstanceNode.id == result["next_node_id"]
            ).first()
            
            if next_instance_node and next_instance_node.approver_id:
                ledger_update["current_approver_id"] = next_instance_node.approver_id
            
            # 记录审计日志 - 拒绝，回退到之前节点
            log_audit(
                action="reject",
                user_id=current_user.id,
                ledger_id=ledger_id,
                workflow_instance_id=workflow_instance.id,
                status_before="pending",
                status_after="pending",
                comment=approval_data.comment
            )
        
        # 更新台账
        if ledger_update:
            ledger = crud.ledger.update(db, db_obj=ledger, obj_in=ledger_update)
    
    else:
        raise HTTPException(status_code=400, detail=f"不支持的审批操作: {approval_data.action}")
    
    # 记录系统日志
    action_text = "通过" if approval_data.action == "approve" else "拒绝"
    LoggerService.log_info(
        db=db,
        module="approval",
        action=approval_data.action,
        message=f"{action_text}审批台账 {ledger.name}",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger_id),
    )
    
    return ledger


@router.post("/ledgers/{ledger_id}/cancel", response_model=schemas.Ledger)
def cancel_approval(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    取消审批流程
    """
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查是否为台账创建者或有管理员权限
    if ledger.created_by_id != current_user.id and not deps.check_permissions("ledger", "admin_approve", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查台账状态
    if ledger.approval_status != "pending":
        raise HTTPException(status_code=400, detail="台账当前不在待审批状态")
    
    # 获取活动的工作流实例
    workflow_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if not workflow_instance:
        raise HTTPException(status_code=400, detail="没有找到活动的审批流程")
    
    # 取消工作流实例
    workflow_instance = crud.workflow_instance.cancel(db, instance_id=workflow_instance.id)
    
    # 更新台账状态
    ledger_update = {
        "approval_status": "cancelled",
        "status": "draft",  # 退回草稿状态
        "current_approver_id": None,
    }
    
    ledger = crud.ledger.update(db, db_obj=ledger, obj_in=ledger_update)
    
    # 记录审计日志
    log_audit(
        action="cancel",
        user_id=current_user.id,
        ledger_id=ledger_id,
        workflow_instance_id=workflow_instance.id,
        status_before="pending",
        status_after="cancelled",
    )
    
    # 记录系统日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="cancel",
        message=f"取消台账 {ledger.name} 的审批流程",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger_id),
    )
    
    return ledger


@router.get("/workflow-instances/{instance_id}", response_model=schemas.WorkflowInstance)
def get_workflow_instance(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流实例详情
    """
    # 获取工作流实例
    workflow_instance = crud.workflow_instance.get(db, id=instance_id)
    if not workflow_instance:
        raise HTTPException(status_code=404, detail="工作流实例不存在")
    
    # 检查是否有权限查看
    ledger = crud.ledger.get(db, id=workflow_instance.ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    if (ledger.created_by_id != current_user.id 
        and ledger.current_approver_id != current_user.id
        and not deps.check_permissions("ledger", "admin_approve", current_user)):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流实例节点
    workflow_instance.nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="view_instance",
        message=f"查看工作流实例 {instance_id}",
        user_id=current_user.id,
        resource_type="workflow_instance",
        resource_id=str(instance_id),
    )
    
    return workflow_instance


@router.get("/audit-logs/{ledger_id}", response_model=List[schemas.AuditLog])
def get_ledger_audit_logs(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账的审计日志
    """
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查是否有权限查看
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取审计日志
    audit_logs = crud.audit_log.get_by_ledger(db, ledger_id=ledger_id)
    
    # 记录系统日志
    LoggerService.log_info(
        db=db,
        module="approval",
        action="view_audit_logs",
        message=f"查看台账 {ledger.name} 的审计日志",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger_id),
    )
    
    return audit_logs 