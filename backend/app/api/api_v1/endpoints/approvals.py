from typing import Any, List, Optional, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.api import deps
from app.models.workflow import WorkflowInstanceNode, WorkflowNode
from app import crud, models, schemas
from app.utils.logger import LoggerService, log_audit

router = APIRouter()


@router.get("/tasks", response_model=List[Dict[str, Any]])
def get_pending_tasks(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的待办任务
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取待办任务
    tasks = crud.workflow_instance_node.get_user_pending_tasks(db, user_id=current_user.id)
    
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
    获取当前用户需要审批的台账列表
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取用户需要审批的台账
    ledgers = []
    
    # 查询用户直接分配为审批人的待审批节点
    direct_assigned_nodes = db.query(models.WorkflowInstanceNode).join(
        models.WorkflowInstance, models.WorkflowInstance.id == models.WorkflowInstanceNode.workflow_instance_id
    ).filter(
        models.WorkflowInstanceNode.approver_id == current_user.id,
        models.WorkflowInstanceNode.status == "pending",
        models.WorkflowInstance.status == "active",
        models.WorkflowInstance.current_node_id == models.WorkflowInstanceNode.id
    ).all()
    
    # 查询用户通过节点多审批人关联的待审批任务
    multi_approve_nodes = db.query(models.WorkflowInstanceNode).join(
        models.WorkflowInstance, models.WorkflowInstance.id == models.WorkflowInstanceNode.workflow_instance_id
    ).join(
        models.WorkflowNode, models.WorkflowNode.id == models.WorkflowInstanceNode.workflow_node_id
    ).join(
        models.workflow_node_approvers, models.workflow_node_approvers.c.workflow_node_id == models.WorkflowNode.id
    ).filter(
        models.workflow_node_approvers.c.user_id == current_user.id,
        models.WorkflowInstanceNode.status == "pending",
        models.WorkflowInstance.status == "active",
        models.WorkflowInstance.current_node_id == models.WorkflowInstanceNode.id,
        models.WorkflowInstanceNode.approver_id.is_(None)
    ).all()
    
    # 合并两种待办任务
    all_pending_nodes = direct_assigned_nodes + multi_approve_nodes
    
    # 获取对应的台账
    ledger_ids = set()
    for node in all_pending_nodes:
        instance = db.query(models.WorkflowInstance).filter(
            models.WorkflowInstance.id == node.workflow_instance_id
        ).first()
        if instance:
            ledger_ids.add(instance.ledger_id)
    
    # 查询台账
    if ledger_ids:
        query = db.query(models.Ledger).filter(models.Ledger.id.in_(ledger_ids))
        
        # 根据状态过滤
        if status:
            query = query.filter(models.Ledger.approval_status == status)
        
        ledgers = query.offset(skip).limit(limit).all()
        
        # 添加额外信息
        for ledger in ledgers:
            # 添加模板名称
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
            if template:
                ledger.template_name = template.name
            
            # 添加创建者名称
            creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
            if creator:
                ledger.creator_name = creator.name
            
            # 添加团队名称
            if ledger.team_id:
                team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
                if team:
                    ledger.team_name = team.name
    
    return ledgers


@router.post("/ledgers/{ledger_id}/submit", response_model=schemas.Ledger)
def submit_ledger_for_approval(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    submit_data: schemas.LedgerSubmit = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    提交台账进入审批流程
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查台账是否属于当前用户或用户所在团队
    if ledger.created_by_id != current_user.id and not crud.user.is_superuser(current_user):
        # 检查用户是否在台账所属团队中
        if ledger.team_id:
            user_teams = [team.id for team in current_user.teams]
            if ledger.team_id not in user_teams:
                raise HTTPException(status_code=403, detail="无权提交此台账")
        else:
            raise HTTPException(status_code=403, detail="无权提交此台账")
    
    # 检查台账状态
    if ledger.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态的台账可以提交审批")
    
    # 检查是否已有活动的工作流实例
    active_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if active_instance:
        raise HTTPException(status_code=400, detail="台账已在审批流程中")
    
    # 确定要使用的工作流 ID
    workflow_id = None
    
    # 1. 首先检查提交数据中是否有指定工作流
    # if submit_data.workflow_id:
    #     workflow_id = submit_data.workflow_id
    # 2. 如果没有指定，检查台账关联的模板是否有默认工作流
    if ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        if template and template.workflow_id:
            workflow_id = template.workflow_id
    
    if not workflow_id:
        raise HTTPException(status_code=400, detail="未找到可用的工作流，无法提交审批")
    
    # 检查工作流是否存在且活动
    workflow = db.query(models.Workflow).filter(
        models.Workflow.id == workflow_id,
        models.Workflow.is_active == True
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="指定的工作流不存在或未激活")
    
    # 创建工作流实例
    # 前端提交时，如果需要指定下一审批人，则需要将next_approver_id传入
    # 如果不需要指定下一审批人，则不传入next_approver_id
    workflow_instance = crud.workflow_instance.create_with_nodes(
        db, workflow_id=workflow_id, ledger_id=ledger_id, created_by=current_user.id, next_approver_id=submit_data.next_approver_id
    )
    
    # 更新台账状态
    ledger.status = "active"
    ledger.approval_status = "pending"
    ledger.submitted_at = datetime.now()
    
    # 更新台账的工作流关联
    # ledger.workflow_id = workflow_id
    
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    
    # 记录审计日志
    log_audit(
        db=db,
        user_id=current_user.id,
        action="submit",
        resource_type="ledger",
        resource_id=ledger_id,
        detail=f"提交台账进入审批流程，工作流实例ID: {workflow_instance.id}",
        old_status="draft",
        new_status="pending"
    )
    
    return ledger


@router.post("/ledgers/{ledger_id}/approve", response_model=schemas.Ledger)
def approve_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    approval_data: schemas.LedgerApproval = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    审批台账
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查台账状态
    if ledger.status != "active" or ledger.approval_status != "pending":
        raise HTTPException(status_code=400, detail="台账不在待审批状态")
    
    # 获取活动的工作流实例
    workflow_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if not workflow_instance:
        raise HTTPException(status_code=400, detail="台账没有活动的工作流实例")
    
    # 获取当前节点
    current_node = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.id == workflow_instance.current_node_id
    ).first()
    
    if not current_node:
        raise HTTPException(status_code=400, detail="工作流实例没有当前节点")
    
    # 获取工作流节点定义
    workflow_node = db.query(models.WorkflowNode).filter(
        models.WorkflowNode.id == current_node.workflow_node_id
    ).first()
    
    if not workflow_node:
        raise HTTPException(status_code=400, detail="工作流节点不存在")
    
    # 检查用户是否有权限审批
    can_approve = False
    
    # 检查是否是指定的审批人
    if current_node.approver_id == current_user.id:
        can_approve = True
    
    # 检查是否在节点的审批人列表中
    if not can_approve and workflow_node.approvers:
        for approver in workflow_node.approvers:
            if approver.id == current_user.id:
                can_approve = True
                break
    
    # 检查是否具有节点指定的审批角色
    if not can_approve and workflow_node.approver_role_id:
        for role in current_user.roles:
            if role.id == workflow_node.approver_role_id:
                can_approve = True
                break
    
    if not can_approve and not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=403, detail="您没有权限审批此台账")
    
    # 根据操作类型处理审批
    if approval_data.action == "approve":
        # 审批通过
        result = crud.workflow_instance.approve_current_node(
            db,
            instance_id=workflow_instance.id,
            user_id=current_user.id,
            comment=approval_data.comment,
            next_approver_id=approval_data.next_approver_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流完成，更新台账状态
        if result.get("workflow_completed"):
            ledger.approval_status = "approved"
            ledger.approved_at = datetime.now()
            db.add(ledger)
            db.commit()
            
            # 记录审计日志
            log_audit(
                db=db,
                user_id=current_user.id,
                action="approve",
                resource_type="ledger",
                resource_id=ledger_id,
                detail=f"台账审批通过，工作流实例ID: {workflow_instance.id}",
                old_status="pending",
                new_status="approved"
            )
        else:
            # 记录审计日志
            log_audit(
                db=db,
                user_id=current_user.id,
                action="approve_node",
                resource_type="ledger",
                resource_id=ledger_id,
                detail=f"台账节点审批通过，工作流实例ID: {workflow_instance.id}, 节点ID: {current_node.id}",
                old_status="pending",
                new_status="pending"
            )
    
    elif approval_data.action == "reject":
        # 审批拒绝
        result = crud.workflow_instance.reject_current_node(
            db,
            instance_id=workflow_instance.id,
            user_id=current_user.id,
            comment=approval_data.comment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流完成（拒绝结束），更新台账状态
        if result.get("workflow_completed"):
            ledger.approval_status = "rejected"
            db.add(ledger)
            db.commit()
            
            # 记录审计日志
            log_audit(
                db=db,
                user_id=current_user.id,
                action="reject",
                resource_type="ledger",
                resource_id=ledger_id,
                detail=f"台账审批拒绝，工作流实例ID: {workflow_instance.id}",
                old_status="pending",
                new_status="rejected"
            )
        else:
            # 记录审计日志
            log_audit(
                db=db,
                user_id=current_user.id,
                action="reject_node",
                resource_type="ledger",
                resource_id=ledger_id,
                detail=f"台账节点审批拒绝，工作流实例ID: {workflow_instance.id}, 节点ID: {current_node.id}",
                old_status="pending",
                new_status="pending"
            )
    
    else:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
    
    # 刷新台账数据
    db.refresh(ledger)
    
    return ledger


@router.post("/ledgers/{ledger_id}/cancel", response_model=schemas.Ledger)
def cancel_approval(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    取消台账审批流程
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查台账是否属于当前用户或用户是否为超级管理员
    if ledger.created_by_id != current_user.id and not crud.user.is_superuser(current_user):
        # 检查用户是否在台账所属团队中且有管理权限
        if ledger.team_id:
            team_member = db.query(models.team_members).filter(
                models.team_members.c.team_id == ledger.team_id,
                models.team_members.c.user_id == current_user.id,
                models.team_members.c.is_admin == True
            ).first()
            
            if not team_member:
                raise HTTPException(status_code=403, detail="无权取消此台账的审批流程")
        else:
            raise HTTPException(status_code=403, detail="无权取消此台账的审批流程")
    
    # 检查台账状态
    if ledger.status != "active" or ledger.approval_status != "pending":
        raise HTTPException(status_code=400, detail="台账不在待审批状态")
    
    # 获取活动的工作流实例
    workflow_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if not workflow_instance:
        raise HTTPException(status_code=400, detail="台账没有活动的工作流实例")
    
    # 取消工作流实例
    workflow_instance = crud.workflow_instance.cancel(db, instance_id=workflow_instance.id)
    
    # 更新台账状态
    ledger.status = "draft"
    ledger.approval_status = "pending"
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    
    # 记录审计日志
    log_audit(
        db=db,
        user_id=current_user.id,
        action="cancel_approval",
        resource_type="ledger",
        resource_id=ledger_id,
        detail=f"取消台账审批流程，工作流实例ID: {workflow_instance.id}",
        old_status="pending",
        new_status="draft"
    )
    
    return ledger


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
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 获取审计日志
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.resource_type == "ledger",
        models.AuditLog.resource_id == str(ledger_id)
    ).order_by(models.AuditLog.created_at.desc()).all()
    
    # 添加用户信息
    for log in logs:
        user = db.query(models.User).filter(models.User.id == log.user_id).first()
        if user:
            log.user_name = user.name
    
    return logs


@router.post("/workflow-instances/{instance_id}/nodes/{node_id}/approve", response_model=Dict[str, Any])
def approve_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    node_id: int = Path(...),
    approval_data: schemas.WorkflowNodeApproval = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    审批通过工作流节点
    """
    try:
        # 检查用户权限
        if not crud.user.is_active(current_user):
            raise HTTPException(status_code=403, detail="用户未激活")
        
        # 获取工作流实例
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 检查工作流实例状态
        if instance.status != "active":
            raise HTTPException(status_code=400, detail="工作流实例已完成或已取消")
        
        # 检查节点是否是当前节点
        if instance.current_node_id != node_id:
            raise HTTPException(status_code=400, detail="只能审批当前节点")
        
        # 获取当前节点
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == node_id
        ).first()
        
        if not current_node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        # 获取工作流节点定义
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == current_node.workflow_node_id
        ).first()
        
        if not workflow_node:
            raise HTTPException(status_code=400, detail="工作流节点不存在")
        
        # 检查用户是否有权限审批
        can_approve = False
        
        # 检查是否是指定的审批人
        if current_node.approver_id == current_user.id:
            can_approve = True
        
        # 检查是否在节点的审批人列表中
        if not can_approve and workflow_node.approvers:
            for approver in workflow_node.approvers:
                if approver.id == current_user.id:
                    can_approve = True
                    break
        
        # 检查是否具有节点指定的审批角色
        if not can_approve and workflow_node.approver_role_id:
            # 获取用户角色
            user_roles = [role.id for role in current_user.roles] if hasattr(current_user, "roles") else []
            if workflow_node.approver_role_id in user_roles:
                can_approve = True
        
        # 超级管理员可以审批所有节点
        if not can_approve and crud.user.is_superuser(current_user):
            can_approve = True
            
        if not can_approve:
            raise HTTPException(status_code=403, detail="您没有权限审批此节点")
        
        # 审批节点
        next_approver_id = getattr(approval_data, "next_approver_id", None)
        result = crud.workflow_instance.approve_current_node(
            db,
            instance_id=instance_id,
            user_id=current_user.id,
            comment=approval_data.comment,
            next_approver_id=next_approver_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流完成，更新台账状态
        if result.get("workflow_completed"):
            ledger = crud.ledger.get(db, id=instance.ledger_id)
            if ledger:
                ledger.approval_status = "approved"
                ledger.approved_at = datetime.now()
                ledger.status = "completed"
                db.add(ledger)
                db.commit()
        
        return result
    except Exception as e:
        import traceback
        error_msg = f"审批节点时发生错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # 打印到控制台
        LoggerService.error(error_msg)  # 记录到日志
        raise


@router.post("/workflow-instances/{instance_id}/nodes/{node_id}/reject", response_model=Dict[str, Any])
def reject_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    node_id: int = Path(...),
    rejection_data: schemas.WorkflowNodeRejection = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    拒绝工作流节点
    """
    try:
        # 检查用户权限
        if not crud.user.is_active(current_user):
            raise HTTPException(status_code=403, detail="用户未激活")
        
        # 获取工作流实例
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 检查工作流实例状态
        if instance.status != "active":
            raise HTTPException(status_code=400, detail="工作流实例已完成或已取消")
        
        # 检查节点是否是当前节点
        if instance.current_node_id != node_id:
            raise HTTPException(status_code=400, detail="只能拒绝当前节点")
        
        # 获取当前节点
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == node_id
        ).first()
        
        if not current_node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        # 获取工作流节点定义
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == current_node.workflow_node_id
        ).first()
        
        if not workflow_node:
            raise HTTPException(status_code=400, detail="工作流节点不存在")
        
        # 检查用户是否有权限拒绝
        can_reject = False
        
        # 检查是否是指定的审批人
        if current_node.approver_id == current_user.id:
            can_reject = True
        
        # 检查是否在节点的审批人列表中
        if not can_reject and workflow_node.approvers:
            for approver in workflow_node.approvers:
                if approver.id == current_user.id:
                    can_reject = True
                    break
        
        # 检查是否具有节点指定的审批角色
        if not can_reject and workflow_node.approver_role_id:
            # 获取用户角色
            user_roles = [role.id for role in current_user.roles] if hasattr(current_user, "roles") else []
            if workflow_node.approver_role_id in user_roles:
                can_reject = True
        
        # 超级管理员可以拒绝所有节点
        if not can_reject and crud.user.is_superuser(current_user):
            can_reject = True
            
        if not can_reject:
            raise HTTPException(status_code=403, detail="您没有权限拒绝此节点")
        
        # 拒绝节点
        result = crud.workflow_instance.reject_current_node(
            db,
            instance_id=instance_id,
            user_id=current_user.id,
            comment=rejection_data.comment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流被拒绝，更新台账状态
        if result.get("workflow_rejected"):
            ledger = crud.ledger.get(db, id=instance.ledger_id)
            if ledger:
                ledger.approval_status = "rejected"
                ledger.status = "returned"
                db.add(ledger)
                db.commit()
        
        return result
    except Exception as e:
        import traceback
        error_msg = f"拒绝节点时发生错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # 打印到控制台
        LoggerService.error(error_msg)  # 记录到日志
        raise 