from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.crud.base import CRUDBase
from app.models.workflow import Workflow, WorkflowNode, WorkflowInstance, WorkflowInstanceNode, ApprovalStatus
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowInstanceCreate, WorkflowInstanceUpdate, WorkflowInstanceNodeCreate, WorkflowInstanceNodeUpdate
from app.models.user import User
from app.models.role import Role
from app.models.ledger import Ledger


class CRUDWorkflow(CRUDBase[Workflow, WorkflowCreate, WorkflowUpdate]):
    def create_with_nodes(self, db: Session, *, obj_in: WorkflowCreate, created_by: int) -> Workflow:
        """创建工作流及其节点"""
        # 首先创建工作流
        workflow_data = obj_in.dict(exclude={"nodes"})
        db_obj = Workflow(**workflow_data)
        db.add(db_obj)
        db.flush()  # 获取工作流ID
        
        # 然后创建工作流节点
        if obj_in.nodes:
            for node_data in obj_in.nodes:
                node_dict = node_data.dict()
                node_dict["workflow_id"] = db_obj.id  # 使用新创建的工作流ID
                db_node = WorkflowNode(**node_dict)
                db.add(db_node)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_by_template(self, db: Session, *, template_id: int) -> List[Workflow]:
        """获取指定模板的所有工作流"""
        return db.query(Workflow).filter(Workflow.template_id == template_id).all()
    
    def get_active_by_template(self, db: Session, *, template_id: int) -> List[Workflow]:
        """获取指定模板的所有活动工作流"""
        return db.query(Workflow).filter(
            Workflow.template_id == template_id,
            Workflow.is_active == True
        ).all()
    
    def deactivate(self, db: Session, *, workflow_id: int) -> Workflow:
        """停用工作流"""
        db_obj = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if db_obj:
            db_obj.is_active = False
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        return db_obj


class CRUDWorkflowNode(CRUDBase[WorkflowNode, WorkflowNodeCreate, WorkflowNodeUpdate]):
    def get_by_workflow(self, db: Session, *, workflow_id: int) -> List[WorkflowNode]:
        """获取工作流的所有节点，按顺序排序"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id
        ).order_by(WorkflowNode.order_index).all()
    
    def get_start_node(self, db: Session, *, workflow_id: int) -> Optional[WorkflowNode]:
        """获取工作流的开始节点"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.order_index == 0
        ).first()
    
    def get_next_node(self, db: Session, *, current_node_id: int) -> Optional[WorkflowNode]:
        """获取下一个节点"""
        current_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node_id).first()
        if not current_node:
            return None
        
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == current_node.workflow_id,
            WorkflowNode.order_index == current_node.order_index + 1
        ).first()
    
    def get_reject_node(self, db: Session, *, current_node_id: int) -> Optional[WorkflowNode]:
        """获取拒绝后应该跳转的节点"""
        current_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node_id).first()
        if not current_node or not current_node.reject_to_node_id:
            return None
        
        return db.query(WorkflowNode).filter(WorkflowNode.id == current_node.reject_to_node_id).first()


class CRUDWorkflowInstance(CRUDBase[WorkflowInstance, WorkflowInstanceCreate, WorkflowInstanceUpdate]):
    def create_with_nodes(
        self, db: Session, *, workflow_id: int, ledger_id: int, created_by: int
    ) -> WorkflowInstance:
        """创建工作流实例及其节点"""
        # 首先创建工作流实例
        db_obj = WorkflowInstance(
            workflow_id=workflow_id,
            ledger_id=ledger_id,
            created_by=created_by,
            status="active"
        )
        db.add(db_obj)
        db.flush()  # 获取实例ID
        
        # 获取工作流的所有节点
        workflow_nodes = db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id
        ).order_by(WorkflowNode.order_index).all()
        
        # 创建实例节点
        instance_nodes = []
        for node in workflow_nodes:
            db_node = WorkflowInstanceNode(
                workflow_instance_id=db_obj.id,
                workflow_node_id=node.id,
                status=ApprovalStatus.PENDING
            )
            
            # 如果是第一个节点(开始节点)，设置为当前节点
            if node.order_index == 0:
                # 设置审批人
                if node.approver_user_id:
                    db_node.approver_id = node.approver_user_id
                elif node.approver_role_id:
                    # 根据角色找审批人，这里简化为取该角色的第一个用户
                    role_user = db.query(User).join(User.roles).filter(
                        Role.id == node.approver_role_id
                    ).first()
                    if role_user:
                        db_node.approver_id = role_user.id
            
            db.add(db_node)
            instance_nodes.append(db_node)
        
        db.flush()
        
        # 设置当前节点为第一个节点
        if instance_nodes:
            db_obj.current_node_id = instance_nodes[0].id
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_by_ledger(self, db: Session, *, ledger_id: int) -> List[WorkflowInstance]:
        """获取台账的所有工作流实例"""
        return db.query(WorkflowInstance).filter(
            WorkflowInstance.ledger_id == ledger_id
        ).all()
    
    def get_active_by_ledger(self, db: Session, *, ledger_id: int) -> Optional[WorkflowInstance]:
        """获取台账的活动工作流实例"""
        return db.query(WorkflowInstance).filter(
            WorkflowInstance.ledger_id == ledger_id,
            WorkflowInstance.status == "active"
        ).first()
    
    def get_with_current_node(self, db: Session, *, instance_id: int) -> Optional[WorkflowInstance]:
        """获取工作流实例及其当前节点"""
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance or not instance.current_node_id:
            return instance
        
        current_node = db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.id == instance.current_node_id
        ).first()
        
        if current_node:
            instance.current_node = current_node
        
        return instance
    
    def approve_current_node(
        self, db: Session, *, instance_id: int, user_id: int, comment: Optional[str] = None,
        next_approver_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """审批通过当前节点，并推进到下一个节点"""
        instance = self.get_with_current_node(db, instance_id=instance_id)
        if not instance:
            return {"success": False, "message": "工作流实例不存在"}
        
        if instance.status != "active":
            return {"success": False, "message": "工作流实例已完成或已取消"}
        
        current_node = instance.current_node
        if not current_node:
            return {"success": False, "message": "当前节点不存在"}
        
        if current_node.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "当前节点已审批"}
        
        # 更新当前节点状态
        current_node.status = ApprovalStatus.APPROVED
        current_node.approver_id = user_id
        current_node.comment = comment
        current_node.completed_at = datetime.now()
        db.add(current_node)
        
        # 获取下一个节点
        workflow_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node.workflow_node_id).first()
        if not workflow_node:
            return {"success": False, "message": "工作流节点不存在"}
        
        next_workflow_node = db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_node.workflow_id,
            WorkflowNode.order_index == workflow_node.order_index + 1
        ).first()
        
        # 如果没有下一个节点，或当前节点是最终节点，则完成工作流
        if not next_workflow_node or workflow_node.is_final:
            instance.status = "completed"
            instance.completed_at = datetime.now()
            db.add(instance)
            db.commit()
            return {"success": True, "message": "审批完成", "workflow_completed": True}
        
        # 创建下一个节点的实例
        next_node = db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.workflow_instance_id == instance.id,
            WorkflowInstanceNode.workflow_node_id == next_workflow_node.id
        ).first()
        
        # 设置下一个审批人
        if next_approver_id:
            next_node.approver_id = next_approver_id
        elif next_workflow_node.approver_user_id:
            next_node.approver_id = next_workflow_node.approver_user_id
        elif next_workflow_node.approver_role_id:
            # 根据角色找审批人
            role_user = db.query(User).join(User.roles).filter(
                Role.id == next_workflow_node.approver_role_id
            ).first()
            if role_user:
                next_node.approver_id = role_user.id
        
        # 更新工作流实例的当前节点
        instance.current_node_id = next_node.id
        db.add(instance)
        db.commit()
        
        return {"success": True, "message": "审批通过", "next_node_id": next_node.id}
    
    def reject_current_node(
        self, db: Session, *, instance_id: int, user_id: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """拒绝当前节点，根据配置决定下一步"""
        instance = self.get_with_current_node(db, instance_id=instance_id)
        if not instance:
            return {"success": False, "message": "工作流实例不存在"}
        
        if instance.status != "active":
            return {"success": False, "message": "工作流实例已完成或已取消"}
        
        current_node = instance.current_node
        if not current_node:
            return {"success": False, "message": "当前节点不存在"}
        
        if current_node.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "当前节点已审批"}
        
        # 更新当前节点状态
        current_node.status = ApprovalStatus.REJECTED
        current_node.approver_id = user_id
        current_node.comment = comment
        current_node.completed_at = datetime.now()
        db.add(current_node)
        
        # 获取当前工作流节点的定义
        workflow_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node.workflow_node_id).first()
        if not workflow_node:
            return {"success": False, "message": "工作流节点不存在"}
        
        # 如果定义了拒绝后跳转的节点，则跳转
        if workflow_node.reject_to_node_id:
            reject_node = db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.workflow_instance_id == instance.id,
                WorkflowInstanceNode.workflow_node_id == workflow_node.reject_to_node_id
            ).first()
            
            if reject_node:
                instance.current_node_id = reject_node.id
                db.add(instance)
                db.commit()
                return {"success": True, "message": "已拒绝，工作流回退", "next_node_id": reject_node.id}
        
        # 如果没有定义拒绝后的跳转，或找不到跳转节点，则完成工作流（拒绝结束）
        instance.status = "rejected"
        instance.completed_at = datetime.now()
        db.add(instance)
        db.commit()
        
        return {"success": True, "message": "已拒绝，工作流结束", "workflow_completed": True}
    
    def cancel(self, db: Session, *, instance_id: int) -> WorkflowInstance:
        """取消工作流实例"""
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if instance and instance.status == "active":
            instance.status = "cancelled"
            instance.completed_at = datetime.now()
            db.add(instance)
            db.commit()
            db.refresh(instance)
        return instance


class CRUDWorkflowInstanceNode(CRUDBase[WorkflowInstanceNode, WorkflowInstanceNodeCreate, WorkflowInstanceNodeUpdate]):
    def get_by_instance(self, db: Session, *, instance_id: int) -> List[WorkflowInstanceNode]:
        """获取工作流实例的所有节点"""
        instance_nodes = db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.workflow_instance_id == instance_id
        ).all()
        
        # 获取工作流节点定义，按顺序排序节点
        if instance_nodes:
            workflow_nodes = db.query(WorkflowNode).filter(
                WorkflowNode.id.in_([node.workflow_node_id for node in instance_nodes])
            ).order_by(WorkflowNode.order_index).all()
            
            # 创建一个映射，将工作流节点ID映射到顺序索引
            order_map = {node.id: node.order_index for node in workflow_nodes}
            
            # 按照工作流节点定义的顺序排序
            instance_nodes.sort(key=lambda x: order_map.get(x.workflow_node_id, 999))
        
        return instance_nodes
    
    def get_by_approver(self, db: Session, *, approver_id: int, status: Optional[str] = None) -> List[WorkflowInstanceNode]:
        """获取指定审批人的所有节点"""
        query = db.query(WorkflowInstanceNode).filter(WorkflowInstanceNode.approver_id == approver_id)
        
        if status:
            query = query.filter(WorkflowInstanceNode.status == status)
        
        return query.all()
    
    def get_user_pending_tasks(self, db: Session, *, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的待审批任务"""
        # 查询用户的待审批节点
        nodes = db.query(WorkflowInstanceNode).join(
            WorkflowInstance, WorkflowInstance.id == WorkflowInstanceNode.workflow_instance_id
        ).filter(
            WorkflowInstanceNode.approver_id == user_id,
            WorkflowInstanceNode.status == ApprovalStatus.PENDING,
            WorkflowInstance.status == "active",
            WorkflowInstance.current_node_id == WorkflowInstanceNode.id
        ).all()
        
        result = []
        for node in nodes:
            # 获取工作流实例
            instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == node.workflow_instance_id).first()
            if not instance:
                continue
            
            # 获取台账信息
            ledger = db.query(Ledger).filter(Ledger.id == instance.ledger_id).first()
            if not ledger:
                continue
            
            # 获取提交人信息
            creator = db.query(User).filter(User.id == instance.created_by).first()
            creator_name = creator.name if creator else "未知"
            
            # 获取工作流节点信息
            workflow_node = db.query(WorkflowNode).filter(WorkflowNode.id == node.workflow_node_id).first()
            node_name = workflow_node.name if workflow_node else "未知节点"
            
            result.append({
                "task_id": node.id,
                "ledger_id": ledger.id,
                "ledger_name": ledger.name,
                "workflow_instance_id": instance.id,
                "workflow_node_name": node_name,
                "created_by": creator_name,
                "created_at": instance.created_at
            })
        
        return result


workflow = CRUDWorkflow(Workflow)
workflow_node = CRUDWorkflowNode(WorkflowNode)
workflow_instance = CRUDWorkflowInstance(WorkflowInstance)
workflow_instance_node = CRUDWorkflowInstanceNode(WorkflowInstanceNode) 