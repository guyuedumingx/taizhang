from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models, schemas
from app.services.workflow.workflow_node_service import workflow_node_service

# 工作流节点路由器 - 只保留审批人相关API
router = APIRouter()

@router.get("/{node_id}", response_model=Dict[str, Any])
def get_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流节点详情
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return workflow_node_service.get_workflow_node(db, node_id=node_id)

@router.get("/{node_id}/approvers", response_model=List[Dict[str, Any]])
def get_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流节点的审批人列表
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 获取节点审批人列表
    approvers = workflow_node_service.get_node_approvers(db, node_id=node_id)
    return approvers

@router.put("/{node_id}/approvers", response_model=Dict[str, Any])
def update_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    user_ids: List[int] = Body(..., embed=True),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新工作流节点的审批人列表
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return workflow_node_service.update_node_approvers(db, node_id=node_id, user_ids=user_ids) 