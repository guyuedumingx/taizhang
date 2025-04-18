from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import crud, models, schemas
from app.api import deps

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
            "order_index": node.order_index,
            "is_final": node.is_final,
            "reject_to_node_id": node.reject_to_node_id,
            "multi_approve_type": node.multi_approve_type,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            # 不使用node.approvers列表
            "approver_ids": [] # 在业务逻辑中另外填充
        }
        
        # 使用 jsonable_encoder 确保所有值都是 JSON 可序列化的
        return jsonable_encoder(node_dict)

    @staticmethod
    def get_workflow_node(db: Session, node_id: int) -> Dict[str, Any]:
        """
        获取工作流节点详情
        """
        node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        # 获取节点基本信息
        node_dict = WorkflowNodeService._serialize_node(node)
        
        # 获取角色信息
        if node.approver_role_id:
            role = db.query(models.Role).filter(models.Role.id == node.approver_role_id).first()
            if role:
                node_dict["approver_role_name"] = role.name
        
        # 获取审批人列表
        approvers = db.query(models.User).join(
            models.workflow_node_approvers,
            models.workflow_node_approvers.c.user_id == models.User.id
        ).filter(
            models.workflow_node_approvers.c.workflow_node_id == node_id
        ).all()
        
        # 将审批人转换为schema
        schema_approvers = []
        approver_ids = []
        for approver in approvers:
            approver_ids.append(approver.id)
            # user_schema = deps.convert_user_to_schema(approver)
            user_schema = approver
            if user_schema:
                schema_approvers.append(jsonable_encoder(user_schema))
        
        # 更新返回字典
        node_dict["approver_ids"] = approver_ids
        node_dict["approvers"] = schema_approvers
        
        return node_dict

    @staticmethod
    def get_node_approvers(db: Session, node_id: int) -> List[Dict[str, Any]]:
        """
        获取工作流节点的审批人列表
        """
        # 检查节点是否存在
        node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        # 从关联表获取审批人列表
        approvers = db.query(models.User).join(
            models.workflow_node_approvers,
            models.workflow_node_approvers.c.user_id == models.User.id
        ).filter(
            models.workflow_node_approvers.c.workflow_node_id == node_id
        ).all()
        
        # 转换为规范化格式
        result = []
        for user in approvers:
            # user_schema = deps.convert_user_to_schema(user)
            user_schema = user
            result.append({
                "id": user.id, 
                "name": user.name,
                "user": jsonable_encoder(user_schema) if user_schema else None
            })
        
        return result

    @staticmethod
    def add_node_approver(db: Session, node_id: int, user_id: int) -> Dict[str, Any]:
        """
        为工作流节点添加审批人
        """
        # 检查节点是否存在
        node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        # 检查用户是否存在
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查用户是否已经是审批人
        existing = db.query(models.workflow_node_approvers).filter(
            models.workflow_node_approvers.c.workflow_node_id == node_id,
            models.workflow_node_approvers.c.user_id == user_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="该用户已经是审批人")
        
        # 添加审批人关系
        db.execute(
            models.workflow_node_approvers.insert().values(
                workflow_node_id=node_id,
                user_id=user_id
            )
        )
        db.commit()
        
        # 获取更新后的节点完整信息
        return WorkflowNodeService.get_workflow_node(db, node_id)

    @staticmethod
    def remove_node_approver(db: Session, node_id: int, user_id: int) -> Dict[str, Any]:
        """
        从工作流节点移除审批人
        """
        # 检查节点是否存在
        node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        # 检查审批人关系是否存在
        existing = db.query(models.workflow_node_approvers).filter(
            models.workflow_node_approvers.c.workflow_node_id == node_id,
            models.workflow_node_approvers.c.user_id == user_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="该用户不是审批人")
        
        # 删除审批人关系
        db.execute(
            models.workflow_node_approvers.delete().where(
                models.workflow_node_approvers.c.workflow_node_id == node_id,
                models.workflow_node_approvers.c.user_id == user_id
            )
        )
        db.commit()
        
        # 获取更新后的节点完整信息
        return WorkflowNodeService.get_workflow_node(db, node_id)

    @staticmethod
    def update_node_approvers(db: Session, node_id: int, user_ids: List[int]) -> Dict[str, Any]:
        """
        更新工作流节点的审批人列表
        """
        # 检查节点是否存在
        node = db.query(models.WorkflowNode).filter(models.WorkflowNode.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="工作流节点不存在")
        
        # 删除所有现有审批人关系
        db.execute(
            models.workflow_node_approvers.delete().where(
                models.workflow_node_approvers.c.workflow_node_id == node_id
            )
        )
        
        # 添加新的审批人关系
        for user_id in user_ids:
            # 检查用户是否存在
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                # 使用直接执行SQL插入而不是ORM关系，避免SQLAlchemy错误
                db.execute(
                    models.workflow_node_approvers.insert().values(
                        workflow_node_id=node_id,
                        user_id=user_id
                    )
                )
        
        db.commit()
        
        # 获取更新后的节点完整信息
        return WorkflowNodeService.get_workflow_node(db, node_id)


workflow_node_service = WorkflowNodeService()