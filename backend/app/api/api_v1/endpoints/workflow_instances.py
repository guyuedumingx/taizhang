from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models, schemas
from app.services.workflow_instance_service import workflow_instance_service

router = APIRouter()

@router.get("/{instance_id}", response_model=schemas.WorkflowInstance)
def get_workflow_instance(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取工作流实例详情"""
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    return workflow_instance_service.get_workflow_instance(db, instance_id, current_user)

@router.get("/ledger/{ledger_id}", response_model=schemas.WorkflowInstance)
def get_workflow_instance_by_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取台账的活动工作流实例"""
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    return workflow_instance_service.get_workflow_instance_by_ledger(db, ledger_id, current_user)

@router.get("/{instance_id}/nodes", response_model=List[schemas.WorkflowInstanceNode])
def get_workflow_instance_nodes(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取工作流实例的所有节点"""
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    return workflow_instance_service.get_workflow_instance_nodes(db, instance_id, current_user)

@router.post("/{instance_id}/nodes/{node_id}/approve", response_model=Dict[str, Any])
def approve_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    node_id: int = Path(...),
    approval_data: schemas.WorkflowNodeApproval = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """审批通过工作流节点"""
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    return workflow_instance_service.approve_workflow_node(db, instance_id, node_id, approval_data, current_user)

@router.post("/{instance_id}/nodes/{node_id}/reject", response_model=Dict[str, Any])
def reject_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    instance_id: int = Path(...),
    node_id: int = Path(...),
    rejection_data: schemas.WorkflowNodeRejection = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """拒绝工作流节点"""
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=403, detail="用户未激活")
    
    return workflow_instance_service.reject_workflow_node(db, instance_id, node_id, rejection_data, current_user) 