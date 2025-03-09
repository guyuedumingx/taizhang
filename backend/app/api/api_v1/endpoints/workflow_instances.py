from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService, log_audit

router = APIRouter()


@router.get("/{instance_id}", response_model=schemas.WorkflowInstance)
def get_workflow_instance(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流实例详情
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取工作流实例
    instance = crud.workflow_instance.get(db, id=instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="工作流实例不存在")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=instance.ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="关联的台账不存在")
    
    # 检查用户是否有权限查看
    if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        # 检查用户是否是审批人
        is_approver = False
        
        # 获取实例的所有节点
        instance_nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
        for node in instance_nodes:
            if node.approver_id == current_user.id:
                is_approver = True
                break
            
            # 检查用户是否在节点的审批人列表中
            workflow_node = db.query(models.WorkflowNode).filter(
                models.WorkflowNode.id == node.workflow_node_id
            ).first()
            
            if workflow_node and workflow_node.approvers:
                for approver in workflow_node.approvers:
                    if approver.id == current_user.id:
                        is_approver = True
                        break
            
            if is_approver:
                break
        
        if not is_approver:
            raise HTTPException(status_code=403, detail="无权查看此工作流实例")
    
    # 获取当前节点
    if instance.current_node_id:
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == instance.current_node_id
        ).first()
        
        if current_node:
            instance.current_node = current_node
            
            # 获取节点定义
            workflow_node = db.query(models.WorkflowNode).filter(
                models.WorkflowNode.id == current_node.workflow_node_id
            ).first()
            
            if workflow_node:
                current_node.node_name = workflow_node.name
                current_node.node_type = workflow_node.node_type
    
    # 获取所有节点
    instance_nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
    instance.nodes = instance_nodes
    
    # 为每个节点添加节点定义信息
    for node in instance.nodes:
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == node.workflow_node_id
        ).first()
        
        if workflow_node:
            node.node_name = workflow_node.name
            node.node_type = workflow_node.node_type
        
        # 添加审批人信息
        if node.approver_id:
            approver = db.query(models.User).filter(models.User.id == node.approver_id).first()
            if approver:
                node.approver_name = approver.name
    
    return instance


@router.get("/ledger/{ledger_id}", response_model=schemas.WorkflowInstance)
def get_workflow_instance_by_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账的活动工作流实例
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 检查用户是否有权限查看
    if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        # 检查用户是否在台账所属团队中
        if ledger.team_id:
            user_teams = [team.id for team in current_user.teams]
            if ledger.team_id not in user_teams:
                raise HTTPException(status_code=403, detail="无权查看此台账的工作流实例")
        else:
            raise HTTPException(status_code=403, detail="无权查看此台账的工作流实例")
    
    # 获取活动的工作流实例
    instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
    if not instance:
        raise HTTPException(status_code=404, detail="台账没有活动的工作流实例")
    
    # 获取当前节点
    if instance.current_node_id:
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == instance.current_node_id
        ).first()
        
        if current_node:
            instance.current_node = current_node
            
            # 获取节点定义
            workflow_node = db.query(models.WorkflowNode).filter(
                models.WorkflowNode.id == current_node.workflow_node_id
            ).first()
            
            if workflow_node:
                current_node.node_name = workflow_node.name
                current_node.node_type = workflow_node.node_type
    
    # 获取所有节点
    instance_nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance.id)
    instance.nodes = instance_nodes
    
    # 为每个节点添加节点定义信息
    for node in instance.nodes:
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == node.workflow_node_id
        ).first()
        
        if workflow_node:
            node.node_name = workflow_node.name
            node.node_type = workflow_node.node_type
        
        # 添加审批人信息
        if node.approver_id:
            approver = db.query(models.User).filter(models.User.id == node.approver_id).first()
            if approver:
                node.approver_name = approver.name
    
    return instance


@router.get("/{instance_id}/nodes", response_model=List[schemas.WorkflowInstanceNode])
def get_workflow_instance_nodes(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流实例的所有节点
    """
    # 检查用户权限
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    # 获取工作流实例
    instance = crud.workflow_instance.get(db, id=instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="工作流实例不存在")
    
    # 获取台账
    ledger = crud.ledger.get(db, id=instance.ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="关联的台账不存在")
    
    # 检查用户是否有权限查看
    if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        # 检查用户是否是审批人
        is_approver = False
        
        # 获取实例的所有节点
        instance_nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
        for node in instance_nodes:
            if node.approver_id == current_user.id:
                is_approver = True
                break
        
        if not is_approver:
            raise HTTPException(status_code=403, detail="无权查看此工作流实例的节点")
    
    # 获取所有节点
    nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
    
    # 为每个节点添加节点定义信息
    for node in nodes:
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == node.workflow_node_id
        ).first()
        
        if workflow_node:
            node.node_name = workflow_node.name
            node.node_type = workflow_node.node_type
        
        # 添加审批人信息
        if node.approver_id:
            approver = db.query(models.User).filter(models.User.id == node.approver_id).first()
            if approver:
                node.approver_name = approver.name
    
    return nodes


@router.post("/{instance_id}/nodes/{node_id}/approve", response_model=Dict[str, Any])
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
    if not can_approve and not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=403, detail="您没有权限审批此节点")
    
    # 审批节点
    result = crud.workflow_instance.approve_current_node(
        db,
        instance_id=instance_id,
        user_id=current_user.id,
        comment=approval_data.comment,
        next_approver_id=approval_data.next_approver_id if hasattr(approval_data, "next_approver_id") else None
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


@router.post("/{instance_id}/nodes/{node_id}/reject", response_model=Dict[str, Any])
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
    if not can_reject and not crud.user.is_superuser(current_user):
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