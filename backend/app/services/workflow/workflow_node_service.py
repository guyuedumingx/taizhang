from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas

class WorkflowNodeService:
    @staticmethod
    def get_workflow_node(db: Session, node_id: int) -> models.WorkflowNode:
        """
        获取工作流节点详情
        """
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

    @staticmethod
    def get_node_approvers(db: Session, node_id: int) -> List[models.User]:
        """
        获取工作流节点的审批人列表
        """
        # 检查节点是否存在
        node = crud.workflow_node.get(db, id=node_id)
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        approvers = crud.workflow_node.get_node_approvers(db, node_id=node_id)
        return approvers

    @staticmethod
    def add_node_approver(db: Session, node_id: int, user_id: int) -> models.WorkflowNode:
        """
        为工作流节点添加审批人
        """
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

    @staticmethod
    def remove_node_approver(db: Session, node_id: int, user_id: int) -> models.WorkflowNode:
        """
        从工作流节点移除审批人
        """
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

    @staticmethod
    def update_node_approvers(db: Session, node_id: int, user_ids: List[int]) -> models.WorkflowNode:
        """
        更新工作流节点的审批人列表
        """
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


workflow_node_service = WorkflowNodeService()