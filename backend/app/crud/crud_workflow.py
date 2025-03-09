from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from app.crud.base import CRUDBase
from app.models.workflow import Workflow, WorkflowNode, workflow_node_approvers
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowNodeCreate, WorkflowNodeCreateWithId, WorkflowNodeUpdate
from app.models.user import User
from app.models.role import Role

class CRUDWorkflow(CRUDBase[Workflow, WorkflowCreate, WorkflowUpdate]):
    def create_with_nodes(self, db: Session, *, obj_in: WorkflowCreate, created_by: int) -> Workflow:
        """创建工作流及其节点"""
        obj_in_data = jsonable_encoder(obj_in, exclude={"nodes"})
        obj_in_data.update({"created_by": created_by})
        
        db_obj = Workflow(**obj_in_data)
        db.add(db_obj)
        db.flush()  # 获取ID但不提交事务
        
        # 创建节点
        if obj_in.nodes:
            for node_data in obj_in.nodes:
                node_data.workflow_id = db_obj.id
                node = CRUDWorkflowNode(WorkflowNode).create_with_approvers(db, obj_in=node_data)
                db_obj.nodes.append(node)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_template(self, db: Session, *, template_id: int) -> List[Workflow]:
        """获取模板的所有工作流"""
        return db.query(Workflow).filter(Workflow.template_id == template_id).all()
    
    def get_active_by_template(self, db: Session, *, template_id: int) -> List[Workflow]:
        """获取模板的活动工作流"""
        return db.query(Workflow).filter(
            Workflow.template_id == template_id,
            Workflow.is_active == True
        ).all()
    
    def deactivate(self, db: Session, *, workflow_id: int) -> Workflow:
        """停用工作流"""
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow:
            workflow.is_active = False
            db.commit()
            db.refresh(workflow)
        return workflow
    
    def update_with_nodes(self, db: Session, *, db_obj: Workflow, obj_in: WorkflowUpdate) -> Workflow:
        """更新工作流及其节点"""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        # 排除节点更新
        nodes_data = update_data.pop("nodes", None)
        
        # 更新基本属性
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # 更新节点
        if nodes_data is not None:
            # 移除所有现有节点
            for node in db_obj.nodes:
                db.delete(node)
            
            # 添加新节点
            for node_data in nodes_data:
                node_data["workflow_id"] = db_obj.id
                node = CRUDWorkflowNode(WorkflowNode).create_with_approvers(db, obj_in=node_data)
                db_obj.nodes.append(node)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_multi_with_filter(self, db: Session, *, skip: int = 0, limit: int = 100, **filters) -> List[Workflow]:
        """根据过滤条件获取多个工作流"""
        query = db.query(Workflow)
        
        # 应用过滤条件
        for field, value in filters.items():
            if hasattr(Workflow, field):
                query = query.filter(getattr(Workflow, field) == value)
        
        return query.offset(skip).limit(limit).all()

class CRUDWorkflowNode(CRUDBase[WorkflowNode, WorkflowNodeCreateWithId, WorkflowNodeUpdate]):
    def get_by_workflow(self, db: Session, *, workflow_id: int) -> List[WorkflowNode]:
        """获取工作流的所有节点"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id
        ).order_by(WorkflowNode.order_index).all()
    
    def get_start_node(self, db: Session, *, workflow_id: int) -> Optional[WorkflowNode]:
        """获取工作流的起始节点"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.node_type == "start"
        ).first()
    
    def get_next_node(self, db: Session, *, workflow_id: int, current_order: int) -> Optional[WorkflowNode]:
        """获取工作流中当前节点的下一个节点"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.order_index > current_order
        ).order_by(WorkflowNode.order_index).first()
    
    def get_reject_node(self, db: Session, *, current_node_id: int) -> Optional[WorkflowNode]:
        """获取当前节点的拒绝回退节点"""
        node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node_id).first()
        if node and node.reject_to_node_id:
            return db.query(WorkflowNode).filter(WorkflowNode.id == node.reject_to_node_id).first()
        return None
    
    def get_node_approvers(self, db: Session, *, node_id: int) -> List[User]:
        """获取工作流节点的所有审批人"""
        # 获取直接关联的审批人
        node = db.query(WorkflowNode).filter(WorkflowNode.id == node_id).first()
        if not node:
            return []
        
        approvers = node.approvers
        
        # 如果有角色关联，也获取该角色的所有用户
        if node.approver_role_id:
            role_users = db.query(User).join(
                User.roles
            ).filter(
                Role.id == node.approver_role_id
            ).all()
            
            # 合并用户列表，去重
            approver_ids = {a.id for a in approvers}
            for user in role_users:
                if user.id not in approver_ids:
                    approvers.append(user)
        
        return approvers
    
    def create_with_approvers(self, db: Session, *, obj_in: Union[WorkflowNodeCreate, WorkflowNodeCreateWithId]) -> WorkflowNode:
        """创建工作流节点及其审批人关联"""
        approver_ids = None
        if hasattr(obj_in, "approver_ids"):
            approver_ids = obj_in.approver_ids
            
        # 转换为字典，排除approver_ids
        if isinstance(obj_in, dict):
            obj_in_data = obj_in.copy()
            obj_in_data.pop("approver_ids", None)
        else:
            obj_in_data = jsonable_encoder(obj_in, exclude={"approver_ids"})
        
        db_obj = WorkflowNode(**obj_in_data)
        db.add(db_obj)
        db.flush()  # 获取ID但不提交
        
        # 添加审批人
        if approver_ids:
            for user_id in approver_ids:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    db_obj.approvers.append(user)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

# 导出实例
workflow = CRUDWorkflow(Workflow)
workflow_node = CRUDWorkflowNode(WorkflowNode)

# 导入并导出工作流实例相关的CRUD类
from app.crud.crud_workflow_instance import CRUDWorkflowInstance, CRUDWorkflowInstanceNode
from app.models.workflow import WorkflowInstance, WorkflowInstanceNode

workflow_instance = CRUDWorkflowInstance(WorkflowInstance)
workflow_instance_node = CRUDWorkflowInstanceNode(WorkflowInstanceNode) 