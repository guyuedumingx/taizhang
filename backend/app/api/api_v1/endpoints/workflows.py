from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models, schemas
from app.utils.logger import LoggerService

router = APIRouter()


@router.get("/", response_model=List[schemas.Workflow])
def read_workflows(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    template_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流列表
    """
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="list",
        message="获取工作流列表",
        user_id=current_user.id,
    )
    
    # 构建查询
    if template_id is not None:
        workflows = crud.workflow.get_by_template(db, template_id=template_id)
        if is_active is not None:
            workflows = [w for w in workflows if w.is_active == is_active]
    else:
        workflows = crud.workflow.get_multi(db, skip=skip, limit=limit)
        if is_active is not None:
            workflows = [w for w in workflows if w.is_active == is_active]
    
    return workflows


@router.post("/", response_model=schemas.Workflow)
def create_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_in: schemas.WorkflowCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建工作流
    """
    # 检查权限
    if not deps.check_permissions("workflow", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 创建工作流
    workflow = crud.workflow.create_with_nodes(
        db=db, obj_in=workflow_in, created_by=current_user.id
    )
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="create",
        message=f"创建工作流 {workflow.name}",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow.id),
    )
    
    return workflow


@router.get("/{workflow_id}", response_model=schemas.Workflow)
def read_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流详情
    """
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 获取工作流节点
    workflow.nodes = crud.workflow_node.get_by_workflow(db, workflow_id=workflow_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="read",
        message=f"查看工作流 {workflow.name}",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow_id),
    )
    
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
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 更新工作流
    workflow = crud.workflow.update(db, db_obj=workflow, obj_in=workflow_in)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="update",
        message=f"更新工作流 {workflow.name}",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow_id),
    )
    
    return workflow


@router.delete("/{workflow_id}", response_model=schemas.Workflow)
def delete_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除工作流
    """
    # 检查权限
    if not deps.check_permissions("workflow", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 检查是否有活动的工作流实例使用此工作流
    instances = db.query(models.WorkflowInstance).filter(
        models.WorkflowInstance.workflow_id == workflow_id,
        models.WorkflowInstance.status == "active"
    ).count()
    
    if instances > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此工作流正在被 {instances} 个活动的实例使用，无法删除"
        )
    
    # 如果不删除，只是停用
    workflow = crud.workflow.deactivate(db, workflow_id=workflow_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="deactivate",
        message=f"停用工作流 {workflow.name}",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow_id),
    )
    
    return workflow


@router.get("/{workflow_id}/nodes", response_model=List[schemas.WorkflowNode])
def read_workflow_nodes(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流节点列表
    """
    # 检查权限
    if not deps.check_permissions("workflow", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 获取节点列表
    nodes = crud.workflow_node.get_by_workflow(db, workflow_id=workflow_id)
    
    return nodes


@router.post("/{workflow_id}/nodes", response_model=schemas.WorkflowNode)
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
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 确保workflow_id匹配
    if node_in.workflow_id != workflow_id:
        node_in.workflow_id = workflow_id
    
    # 创建节点
    node = crud.workflow_node.create(db, obj_in=node_in)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="create_node",
        message=f"创建工作流节点 {node.name}",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node.id),
    )
    
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
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 更新节点
    node = crud.workflow_node.update(db, db_obj=node, obj_in=node_in)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="update_node",
        message=f"更新工作流节点 {node.name}",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id),
    )
    
    return node


@router.delete("/{workflow_id}/nodes/{node_id}", response_model=schemas.WorkflowNode)
def delete_workflow_node(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    node_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除工作流节点
    """
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取节点
    node = crud.workflow_node.get(db, id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="工作流节点不存在")
    
    # 确保节点属于指定的工作流
    if node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="节点不属于指定的工作流")
    
    # 检查是否有工作流实例正在使用此节点
    instance_nodes = db.query(models.WorkflowInstanceNode).filter(
        models.WorkflowInstanceNode.workflow_node_id == node_id
    ).count()
    
    if instance_nodes > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此节点正在被 {instance_nodes} 个工作流实例节点使用，无法删除"
        )
    
    # 删除节点
    node = crud.workflow_node.remove(db, id=node_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="delete_node",
        message=f"删除工作流节点 {node.name}",
        user_id=current_user.id,
        resource_type="workflow_node",
        resource_id=str(node_id),
    )
    
    return node


@router.post("/{workflow_id}/deactivate", response_model=schemas.Workflow)
def deactivate_workflow(
    *,
    db: Session = Depends(deps.get_db),
    workflow_id: int = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    停用工作流（即使正在被使用）
    """
    # 检查权限
    if not deps.check_permissions("workflow", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取工作流
    workflow = crud.workflow.get(db, id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 停用工作流
    workflow = crud.workflow.deactivate(db, workflow_id=workflow_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="workflow",
        action="deactivate",
        message=f"停用工作流 {workflow.name}",
        user_id=current_user.id,
        resource_type="workflow",
        resource_id=str(workflow_id),
    )
    
    # 获取工作流节点
    workflow.nodes = crud.workflow_node.get_by_workflow(db, workflow_id=workflow_id)
    
    return workflow 