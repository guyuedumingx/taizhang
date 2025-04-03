from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import crud, models, schemas

class WorkflowNodeService:
    @staticmethod
    def _serialize_node(node: models.WorkflowNode) -> Dict[str, Any]:
        """
        序列化工作流节点，返回可JSON序列化的字典
        """
        # 创建一个包含基本信息的字典
        node_dict = {
            "id": node.id,
            "workflow_id": node.workflow_id,
            "name": node.name,
            "description": node.description,
            "node_type": node.node_type,
            "approver_role_id": node.approver_role_id,
            "approver_user_id": node.approver_user_id,
            "order_index": node.order_index,
            "is_final": node.is_final,
            "reject_to_node_id": node.reject_to_node_id,
            "multi_approve_type": node.multi_approve_type,
            "need_select_next_approver": node.need_select_next_approver,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "approver_ids": [user.id for user in node.approvers]
        }
        
        # 使用 jsonable_encoder 确保所有值都是 JSON 可序列化的
        return jsonable_encoder(node_dict)

    @staticmethod
    def get_workflow_node(db: Session, node_id: int) -> Dict[str, Any]:
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
        
        return WorkflowNodeService._serialize_node(node)

    @staticmethod
    def get_node_approvers(db: Session, node_id: int) -> List[Dict[str, Any]]:
        """
        获取工作流节点的审批人列表
        """
        # 检查节点是否存在
        node = crud.workflow_node.get(db, id=node_id)
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        approvers = crud.workflow_node.get_node_approvers(db, node_id=node_id)
        return jsonable_encoder([{"id": user.id, "name": user.name} for user in approvers])

    @staticmethod
    def add_node_approver(db: Session, node_id: int, user_id: int) -> Dict[str, Any]:
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
        
        return WorkflowNodeService._serialize_node(node)

    @staticmethod
    def remove_node_approver(db: Session, node_id: int, user_id: int) -> Dict[str, Any]:
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
        
        return WorkflowNodeService._serialize_node(node)

    @staticmethod
    def update_node_approvers(db: Session, node_id: int, user_ids: List[int]) -> Dict[str, Any]:
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
        
        return WorkflowNodeService._serialize_node(node)


workflow_node_service = WorkflowNodeService()