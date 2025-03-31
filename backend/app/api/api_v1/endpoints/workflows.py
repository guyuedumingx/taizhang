from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService
from fastapi.encoders import jsonable_encoder
from app.services.workflow.workflow_service import workflow_service

# 主工作流路由器
router = APIRouter()

# 节点路由器 - 将其移至专门的文件中
node_router = APIRouter()

@router.get("/", response_model=schemas.PaginatedResponse[schemas.Workflow])
def read_workflows(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取工作流列表"""
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    workflows = workflow_service.get_workflows(db, skip=skip, limit=limit)
    total = db.query(models.Workflow).count()
    
    return {
        "items": workflows,
        "total": total,
        "page": skip // limit + 1,
        "size": limit
    }

@router.post("/", response_model=schemas.Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_in: schemas.WorkflowCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新工作流
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "create"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 验证工作流名称不能为空
    if not workflow_in.name or workflow_in.name.strip() == "":
        raise HTTPException(status_code=422, detail="工作流名称不能为空")
    
    # 创建工作流
    workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=current_user.id)
    
    return workflow

@router.get("/{workflow_id}", response_model=schemas.Workflow)
def read_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定工作流
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # # 添加模板名称
    # template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
    # if template:
    #     workflow.template_name = template.name
    
    return workflow

@router.put("/{workflow_id}", response_model=schemas.Workflow)
def update_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    workflow_in: schemas.WorkflowUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新工作流
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 更新工作流
    workflow = crud.workflow.update_with_nodes(db, db_obj=workflow, obj_in=workflow_in)
    
    # # 添加模板名称
    # template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
    # if template:
    #     workflow.template_name = template.name
    
    return workflow

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    删除工作流
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "delete"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 检查是否有台账在使用该工作流
    ledgers = db.query(models.Ledger).filter(models.Ledger.workflow_id == workflow_id).all()
    if ledgers:
        raise HTTPException(status_code=400, detail="该工作流已被台账使用，不能删除")
    
    # 删除工作流
    crud.workflow.remove(db, id=workflow_id)
    
    return None

@router.get("/{workflow_id}/nodes", response_model=List[schemas.WorkflowNode])
def read_workflow_nodes(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流的所有节点
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    nodes = crud.workflow_node.get_by_workflow(db, workflow_id=workflow_id)
    
    # 获取每个节点的审批人信息
    for node in nodes:
        approvers = crud.workflow_node.get_node_approvers(db, node_id=node.id)
        node.approvers = approvers
        if node.approver_role_id:
            role = db.query(models.Role).filter(models.Role.id == node.approver_role_id).first()
            if role:
                node.approver_role_name = role.name
        if node.approver_user_id:
            user = db.query(models.User).filter(models.User.id == node.approver_user_id).first()
            if user:
                node.approver_user_name = user.name
    
    return nodes

@router.post("/{workflow_id}/nodes", response_model=schemas.WorkflowNode, status_code=status.HTTP_201_CREATED)
def create_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_in: schemas.WorkflowNodeCreateWithId,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建工作流节点
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查工作流是否存在
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 设置workflow_id
    node_in.workflow_id = workflow_id
    
    # 创建节点
    node = crud.workflow_node.create_with_approvers(db, obj_in=node_in)
    
    return node

@router.put("/{workflow_id}/nodes/{node_id}", response_model=schemas.WorkflowNode)
def update_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    node_in: schemas.WorkflowNodeUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新工作流节点
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 更新节点
    node = crud.workflow_node.update(db, db_obj=node, obj_in=node_in)
    
    return node

@router.delete("/{workflow_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    删除工作流节点
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 删除节点
    crud.workflow_node.remove(db, id=node_id)
    
    return None

@router.post("/{workflow_id}/deactivate", response_model=schemas.Workflow)
def deactivate_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    停用工作流
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 停用工作流
    workflow = crud.workflow.deactivate(db, workflow_id=workflow_id)
    
    # 添加模板名称
    # template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
    # if template:
    #     workflow.template_name = template.name
    
    return workflow

# ==========================================================
# 工作流节点路由
# ==========================================================

@node_router.get("/{node_id}", response_model=schemas.WorkflowNode)
def get_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流节点详情
    """
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="view_node",
        message=f"查看工作流节点 {node.name}",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id),
    )
    
    return node


@node_router.get("/{node_id}/approvers", response_model=List[schemas.User])
def get_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流节点的审批人列表
    """
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="view_node_approvers",
        message=f"查看工作流节点 {node_id} 的审批人列表",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id)
    )
    
    # 返回节点的审批人列表
    return node.approvers


@node_router.post("/{node_id}/approvers", response_model=schemas.WorkflowNode)
def add_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    approver_ids: List[int] = Body(..., title="审批人ID列表"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    添加工作流节点审批人
    """
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 获取所有用户
    users = []
    for user_id in approver_ids:
        user = crud.user.get(db, id=user_id)
        if user:
            users.append(user)
        else:
            raise HTTPException(status_code=404, detail=f"用户ID {user_id} 不存在")
    
    # 添加审批人
    for user in users:
        if user not in node.approvers:
            node.approvers.append(user)
    
    db.commit()
    db.refresh(node)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="add_node_approvers",
        message=f"为工作流节点 {node.name} 添加审批人",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id)
    )
    
    return node


@node_router.delete("/{node_id}/approvers", response_model=schemas.WorkflowNode)
def remove_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    approver_ids: List[int] = Body(..., title="要移除的审批人ID列表"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    移除工作流节点审批人
    """
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 获取已存在的审批人
    existing_approvers = {approver.id: approver for approver in node.approvers}
    
    # 移除审批人
    for user_id in approver_ids:
        if user_id in existing_approvers:
            node.approvers.remove(existing_approvers[user_id])
    
    db.commit()
    db.refresh(node)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="remove_node_approvers",
        message=f"从工作流节点 {node.name} 移除审批人",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id)
    )
    
    return node


@node_router.put("/{node_id}/approvers", response_model=schemas.WorkflowNode)
def update_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    node_id: int = Path(..., title="工作流节点ID"),
    approver_ids: List[int] = Body(..., title="审批人ID列表"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新工作流节点审批人（替换原有列表）
    """
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 清除现有审批人
    node.approvers = []
    
    # 获取所有用户并添加为审批人
    for user_id in approver_ids:
        user = crud.user.get(db, id=user_id)
        if user:
            node.approvers.append(user)
        else:
            raise HTTPException(status_code=404, detail=f"用户ID {user_id} 不存在")
    
    db.commit()
    db.refresh(node)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="update_node_approvers",
        message=f"更新工作流节点 {node.name} 的审批人",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id)
    )
    
    return node

@router.post("/{workflow_id}/nodes/{node_id}/approvers", response_model=schemas.WorkflowNode)
def add_node_approver(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    user_id: int = Body(..., embed=True),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    添加节点审批人
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 检查用户是否存在
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 添加审批人
    crud.workflow_node.add_approver(db, node_id=node_id, user_id=user_id)
    
    return node

@router.get("/{workflow_id}/nodes/{node_id}/approvers", response_model=List[schemas.User])
def get_node_approvers(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取节点审批人列表
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 获取审批人列表
    approvers = crud.workflow_node.get_node_approvers(db, node_id=node_id)
    
    return approvers

@router.delete("/{workflow_id}/nodes/{node_id}/approvers", status_code=status.HTTP_204_NO_CONTENT)
def remove_node_approver(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    user_id: int = Query(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    移除节点审批人
    """
    # 检查用户权限
    if not crud.user.is_superuser(current_user) and not crud.user.has_role_permission(current_user, "workflow", "update"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查节点是否存在
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 检查用户是否存在
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 移除审批人
    crud.workflow_node.remove_approver(db, node_id=node_id, user_id=user_id)
    
    return None

# 将节点路由器注册到主路由器
router.include_router(node_router, prefix="/nodes", tags=["工作流节点管理"]) 