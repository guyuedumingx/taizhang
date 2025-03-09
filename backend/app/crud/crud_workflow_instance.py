from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from app.crud.base import CRUDBase
from app.models.workflow import (
    WorkflowInstance, WorkflowInstanceNode, WorkflowNode, 
    workflow_node_approvers, ApprovalStatus
)
from app.schemas.workflow import (
    WorkflowInstanceCreate, WorkflowInstanceUpdate, 
    WorkflowInstanceNodeCreate, WorkflowInstanceNodeUpdate
)
from app.models.user import User
from app.models.role import Role
from app.models.ledger import Ledger

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
        return (
            db.query(self.model)
            .filter(self.model.ledger_id == ledger_id)
            .order_by(desc(self.model.created_at))
            .all()
        )
    
    def get_active_by_ledger(self, db: Session, *, ledger_id: int) -> Optional[WorkflowInstance]:
        """获取台账的活动工作流实例"""
        return (
            db.query(self.model)
            .filter(
                self.model.ledger_id == ledger_id,
                self.model.status == "active"
            )
            .first()
        )
    
    def get_with_current_node(self, db: Session, *, instance_id: int) -> Optional[WorkflowInstance]:
        """获取工作流实例及其当前节点"""
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance or not instance.current_node_id:
            return instance
        
        current_node = db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.id == instance.current_node_id
        ).first()
        
        # 不直接设置current_node属性，而是返回一个带有current_node的结果
        if current_node:
            # 直接返回原始实例和节点，不进行序列化和反序列化
            # 这样可以避免日期时间字段转换问题
            instance.__dict__["_current_node"] = current_node
            return instance
        
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
        
        # 从实例对象的__dict__中获取_current_node，或者重新查询
        current_node = instance.__dict__.get("_current_node")
        if not current_node:
            current_node = db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.id == instance.current_node_id
            ).first()
            
        if not current_node:
            return {"success": False, "message": "当前节点不存在"}
        
        if current_node.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "当前节点已审批"}
        
        # 获取当前工作流节点定义
        workflow_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node.workflow_node_id).first()
        if not workflow_node:
            return {"success": False, "message": "工作流节点不存在"}
        
        # 记录审批操作
        if not current_node.approver_actions:
            current_node.approver_actions = []
        
        current_node.approver_actions.append({
            "user_id": user_id,
            "action": "approve",
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        })
        
        # 检查是否需要多人审批
        multi_approve_required = False
        all_approved = True
        
        # 获取节点的所有审批人
        node_approvers = db.query(workflow_node_approvers).filter(
            workflow_node_approvers.c.workflow_node_id == workflow_node.id
        ).all()
        
        if len(node_approvers) > 1:
            multi_approve_required = True
            
            # 获取已审批的用户ID
            approved_user_ids = set()
            for action in current_node.approver_actions:
                if action.get("action") == "approve":
                    approved_user_ids.add(action.get("user_id"))
            
            # 检查是否所有审批人都已审批
            if workflow_node.multi_approve_type == "all":
                # 需要所有人审批
                for approver in node_approvers:
                    if approver.user_id not in approved_user_ids:
                        all_approved = False
                        break
            else:  # "any" 或其他值，任一人审批即可
                all_approved = True
        
        # 如果需要多人审批且尚未全部审批完成，则只记录操作，不更改状态
        if multi_approve_required and not all_approved:
            # 设置当前审批人为此次操作的用户
            current_node.approver_id = user_id
            db.add(current_node)
            db.commit()
            return {
                "success": True, 
                "message": "审批记录已添加，等待其他审批人操作", 
                "multi_approve": True,
                "all_approved": False
            }
        
        # 更新当前节点状态
        current_node.status = ApprovalStatus.APPROVED
        current_node.approver_id = user_id
        current_node.comment = comment
        current_node.completed_at = datetime.now()
        db.add(current_node)
        
        # 获取下一个节点
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
        
        if not next_node:
            return {"success": False, "message": "下一个节点不存在"}
        
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
        db.refresh(instance)  # 刷新实例以确保关系正确加载
        
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
        
        # 从实例对象的__dict__中获取_current_node，或者重新查询
        current_node = instance.__dict__.get("_current_node")
        if not current_node:
            current_node = db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.id == instance.current_node_id
            ).first()
            
        if not current_node:
            return {"success": False, "message": "当前节点不存在"}
        
        if current_node.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "当前节点已审批"}
        
        # 获取当前工作流节点的定义
        workflow_node = db.query(WorkflowNode).filter(WorkflowNode.id == current_node.workflow_node_id).first()
        if not workflow_node:
            return {"success": False, "message": "工作流节点不存在"}
        
        # 记录拒绝操作
        if not current_node.approver_actions:
            current_node.approver_actions = []
        
        current_node.approver_actions.append({
            "user_id": user_id,
            "action": "reject",
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        })
        
        # 在多审批人场景下，任何一人拒绝即可拒绝整个节点
        # 不需要等待所有人都操作
        
        # 更新当前节点状态
        current_node.status = ApprovalStatus.REJECTED
        current_node.approver_id = user_id
        current_node.comment = comment
        current_node.completed_at = datetime.now()
        db.add(current_node)
        
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
                db.refresh(instance)  # 刷新实例以确保关系正确加载
                return {"success": True, "message": "已拒绝，工作流回退", "next_node_id": reject_node.id}
        
        # 如果没有定义拒绝后的跳转，或找不到跳转节点，则完成工作流（拒绝结束）
        instance.status = "rejected"
        instance.completed_at = datetime.now()
        db.add(instance)
        db.commit()
        
        return {"success": True, "message": "已拒绝，工作流结束", "workflow_rejected": True}
    
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
        return (
            db.query(self.model)
            .filter(self.model.workflow_instance_id == instance_id)
            .order_by(self.model.created_at)
            .all()
        )
    
    def get_by_approver(self, db: Session, *, approver_id: int, status: Optional[str] = None) -> List[WorkflowInstanceNode]:
        """获取指定审批人的所有节点"""
        query = db.query(self.model).filter(self.model.approver_id == approver_id)
        
        if status:
            query = query.filter(self.model.status == status)
        
        return query.all()
    
    def get_user_pending_tasks(self, db: Session, *, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的待审批任务"""
        # 查询用户直接分配为审批人的待审批节点
        direct_assigned_nodes = db.query(self.model).join(
            WorkflowInstance, WorkflowInstance.id == self.model.workflow_instance_id
        ).filter(
            self.model.approver_id == user_id,
            self.model.status == ApprovalStatus.PENDING,
            WorkflowInstance.status == "active",
            WorkflowInstance.current_node_id == self.model.id
        ).all()
        
        # 查询用户通过节点多审批人关联的待审批任务
        # 这部分是新增的，查询用户是workflow_node.approvers中的用户，
        # 且对应的工作流实例节点正在等待审批
        multi_approve_nodes = db.query(self.model).join(
            WorkflowInstance, WorkflowInstance.id == self.model.workflow_instance_id
        ).join(
            WorkflowNode, WorkflowNode.id == self.model.workflow_node_id
        ).join(
            workflow_node_approvers, workflow_node_approvers.c.workflow_node_id == WorkflowNode.id
        ).filter(
            workflow_node_approvers.c.user_id == user_id,
            self.model.status == ApprovalStatus.PENDING,
            WorkflowInstance.status == "active",
            WorkflowInstance.current_node_id == self.model.id,
            # 下面这个条件确保工作流实例节点没有直接指定审批人
            # 如果已经指定审批人，就不应通过多审批人机制再次出现在待办中
            self.model.approver_id.is_(None)
        ).all()
        
        # 合并两种待办任务
        all_pending_nodes = direct_assigned_nodes + multi_approve_nodes
        
        result = []
        for node in all_pending_nodes:
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
            
            # 获取审批类型
            multi_approve_type = workflow_node.multi_approve_type if workflow_node else "any"
            
            # 获取已经审批的用户数量和总共需要的审批人数
            approved_count = 0
            total_approver_count = 0
            
            if node.approver_actions:
                # 计算已经审批的用户数量
                approved_users = set()
                for action in node.approver_actions:
                    if action.get("action") == "approve":
                        approved_users.add(action.get("user_id"))
                approved_count = len(approved_users)
            
            # 获取节点审批人总数
            if workflow_node:
                total_approver_count = db.query(workflow_node_approvers).filter(
                    workflow_node_approvers.c.workflow_node_id == workflow_node.id
                ).count()
                
                # 如果节点没有通过审批人关联表设置审批人，但有指定审批角色或用户，则总数为1
                if total_approver_count == 0 and (workflow_node.approver_role_id or workflow_node.approver_user_id):
                    total_approver_count = 1
            
            result.append({
                "task_id": node.id,
                "ledger_id": ledger.id,
                "ledger_name": ledger.name,
                "workflow_instance_id": instance.id,
                "workflow_node_name": node_name,
                "created_by": creator_name,
                "created_at": instance.created_at,
                "multi_approve_type": multi_approve_type,
                "approved_count": approved_count,
                "total_approver_count": total_approver_count
            })
        
        return result

    def add_approver_action(
        self, 
        db: Session, 
        *, 
        instance_node_id: int, 
        user_id: int, 
        action: str, 
        comment: Optional[str] = None
    ) -> WorkflowInstanceNode:
        """添加审批人操作记录"""
        node = db.query(self.model).filter(self.model.id == instance_node_id).first()
        if not node:
            return None
            
        # 获取用户信息
        user = db.query(User).filter(User.id == user_id).first()
        user_name = user.name if user else f"用户 {user_id}"
        
        # 创建操作记录
        action_record = {
            "user_id": user_id,
            "user_name": user_name,
            "action": action,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }
        
        # 更新节点记录
        if not node.approver_actions:
            node.approver_actions = []
        node.approver_actions.append(action_record)
        
        db.commit()
        db.refresh(node)
        return node

# 导出实例
workflow_instance = CRUDWorkflowInstance(WorkflowInstance)
workflow_instance_node = CRUDWorkflowInstanceNode(WorkflowInstanceNode) 