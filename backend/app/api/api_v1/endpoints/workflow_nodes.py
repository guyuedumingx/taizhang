from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService

# 工作流节点路由器 - 只保留审批人相关API
router = APIRouter()

@router.get("/{node_id}", response_model=schemas.WorkflowNode)
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
    
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 获取审批人信息
    approvers = crud.workflow_node.get_node_approvers(db, node_id=node.id)
    node.approvers = approvers
    
    if node.approver_user_id:
        user = db.query(models.User).filter(models.User.id == node.approver_user_id).first()
        if user:
            node.approver_user_name = user.name
    
    return node

@router.get("/{node_id}/approvers", response_model=List[schemas.User])
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
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    approvers = crud.workflow_node.get_node_approvers(db, node_id=node_id)
    return approvers

@router.post("/{node_id}/approvers", response_model=schemas.WorkflowNode)
def add_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    user_id: int = Body(..., embed=True),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    为工作流节点添加审批人
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 检查用户是否存在
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查用户是否已经是审批人
    current_approvers = node.approvers
    current_approver_ids = [user.id for user in current_approvers]
    
    if user_id in current_approver_ids:
        raise HTTPException(status_code=400, detail="该用户已经是审批人")
    
    # 添加审批人
    node.approvers.append(user)
    db.commit()
    db.refresh(node)
    
    return node

@router.delete("/{node_id}/approvers", response_model=schemas.WorkflowNode)
def remove_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    user_id: int = Query(..., title="用户ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    从工作流节点移除审批人
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 检查用户是否存在
    user = crud.user.get(db, id=user_id)
    if user and user in node.approvers:
        node.approvers.remove(user)
        db.commit()
        db.refresh(node)
    else:
        raise HTTPException(status_code=404, detail="该用户不是审批人")
    
    return node

@router.put("/{node_id}/approvers", response_model=schemas.WorkflowNode)
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
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 清空现有审批人
    node.approvers = []
    
    # 添加新的审批人
    for user_id in user_ids:
        user = crud.user.get(db, id=user_id)
        if user:
            node.approvers.append(user)
    
    db.commit()
    db.refresh(node)
    
    return node 