from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.utils.logger import LoggerService

class WorkflowService:
    @staticmethod
    def get_workflows(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        template_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[models.Workflow]:
        """
        获取工作流列表
        """
        # 构建查询条件
        filters = {}
        if template_id is not None:
            filters["template_id"] = template_id
        if is_active is not None:
            filters["is_active"] = is_active
            
        workflows = crud.workflow.get_multi_with_filter(db, skip=skip, limit=limit, **filters)
        
        # 为每个工作流添加相关信息并处理序列化
        result = []
        for workflow in workflows:
            # 添加模板名称
            template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
            if template:
                workflow.template_name = template.name
            
            # 创建工作流字典
            workflow_dict = {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "template_id": workflow.template_id,
                "template_name": getattr(workflow, "template_name", None),
                "is_active": workflow.is_active,
                "created_by": workflow.created_by,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
                "nodes": []
            }
            
            # 处理节点
            for node in workflow.nodes:
                node_dict = {
                    "id": node.id,
                    "name": node.name,
                    "description": node.description,
                    "node_type": node.node_type,
                    "workflow_id": node.workflow_id,
                    "approver_role_id": node.approver_role_id,
                    "approver_user_id": node.approver_user_id,
                    "order_index": node.order_index,
                    "is_final": node.is_final,
                    "reject_to_node_id": node.reject_to_node_id,
                    "multi_approve_type": node.multi_approve_type,
                    "need_select_next_approver": node.need_select_next_approver,
                    "created_at": node.created_at,
                    "updated_at": node.updated_at,
                    "approver_role_name": getattr(node, "approver_role_name", None),
                    "approver_user_name": getattr(node, "approver_user_name", None),
                    "approvers": []
                }
                
                # 处理审批人
                for approver in node.approvers:
                    node_dict["approvers"].append({
                        "id": approver.id,
                        "name": approver.name,
                        "username": approver.username
                    })
                
                workflow_dict["nodes"].append(node_dict)
            
            result.append(workflow_dict)
        
        return result

    @staticmethod
    def create_workflow(
        db: Session,
        workflow_in: schemas.WorkflowCreate,
        created_by: int
    ) -> models.Workflow:
        """
        创建新工作流
        """
        # 验证工作流名称不能为空
        if not workflow_in.name or workflow_in.name.strip() == "":
            raise HTTPException(status_code=422, detail="工作流名称不能为空")
        
        # 检查模板是否存在
        template = crud.template.get(db, id=workflow_in.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 创建工作流
        workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=created_by)
        
        # 添加模板名称
        workflow.template_name = template.name
        
        return workflow

    @staticmethod
    def get_workflow(db: Session, workflow_id: int) -> models.Workflow:
        """
        获取指定工作流
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 添加模板名称
        template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
        if template:
            workflow.template_name = template.name
        
        return workflow

    @staticmethod
    def update_workflow(
        db: Session, 
        workflow_id: int, 
        workflow_in: schemas.WorkflowUpdate
    ) -> models.Workflow:
        """
        更新工作流
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 更新工作流
        workflow = crud.workflow.update_with_nodes(db, db_obj=workflow, obj_in=workflow_in)
        
        # 添加模板名称
        template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
        if template:
            workflow.template_name = template.name
        
        return workflow

    @staticmethod
    def delete_workflow(db: Session, workflow_id: int) -> models.Workflow:
        """
        删除工作流
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 检查是否有关联的工作流实例
        workflow_instances = db.query(models.WorkflowInstance).filter(
            models.WorkflowInstance.workflow_id == workflow_id
        ).count()
        
        if workflow_instances > 0:
            raise HTTPException(status_code=400, detail="该工作流已被使用，无法删除")
        
        return crud.workflow.remove(db, id=workflow_id)

    @staticmethod
    def get_workflow_nodes(db: Session, workflow_id: int) -> List[models.WorkflowNode]:
        """
        获取工作流的所有节点
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        nodes = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.workflow_id == workflow_id
        ).order_by(models.WorkflowNode.order_index).all()
        
        for node in nodes:
            # 获取审批人信息
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

    @staticmethod
    def create_workflow_node(
        db: Session, 
        workflow_id: int, 
        node_in: schemas.WorkflowNodeCreateWithId
    ) -> models.WorkflowNode:
        """
        添加工作流节点
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 检查节点类型
        if node_in.node_type not in ["start", "approval", "end"]:
            raise HTTPException(status_code=422, detail="节点类型必须是start, approval或end")
        
        # 创建工作流节点
        node = crud.workflow_node.create_with_id(db, obj_in=node_in, workflow_id=workflow_id)
        
        # 获取审批人信息
        if node.approver_role_id:
            role = db.query(models.Role).filter(models.Role.id == node.approver_role_id).first()
            if role:
                node.approver_role_name = role.name
        
        if node.approver_user_id:
            user = db.query(models.User).filter(models.User.id == node.approver_user_id).first()
            if user:
                node.approver_user_name = user.name
        
        return node

    @staticmethod
    def update_workflow_node(
        db: Session, 
        workflow_id: int, 
        node_id: int, 
        node_in: schemas.WorkflowNodeUpdate
    ) -> models.WorkflowNode:
        """
        更新工作流节点
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        node = crud.workflow_node.get(db, id=node_id)
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        if node.workflow_id != workflow_id:
            raise HTTPException(status_code=400, detail="节点不属于该工作流")
        
        # 更新节点
        node = crud.workflow_node.update(db, db_obj=node, obj_in=node_in)
        
        # 获取审批人信息
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
        
        return node

    @staticmethod
    def delete_workflow_node(db: Session, workflow_id: int, node_id: int) -> models.WorkflowNode:
        """
        删除工作流节点
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        node = crud.workflow_node.get(db, id=node_id)
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        if node.workflow_id != workflow_id:
            raise HTTPException(status_code=400, detail="节点不属于该工作流")
        
        # 删除节点
        return crud.workflow_node.remove(db, id=node_id)

    @staticmethod
    def deactivate_workflow(db: Session, workflow_id: int) -> models.Workflow:
        """
        停用工作流
        """
        workflow = crud.workflow.get(db, id=workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        if not workflow.is_active:
            raise HTTPException(status_code=400, detail="工作流已经是停用状态")
        
        # 停用工作流
        workflow.is_active = False
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # 添加模板名称
        template = db.query(models.Template).filter(models.Template.id == workflow.template_id).first()
        if template:
            workflow.template_name = template.name
        
        return workflow


workflow_service = WorkflowService() 