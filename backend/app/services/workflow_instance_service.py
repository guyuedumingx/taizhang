from typing import Any, List, Optional, Dict
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app import crud, models, schemas
from app.utils.logger import LoggerService, log_audit
from app.api import deps
from app.services.workflow_node_service import WorkflowNodeService


class WorkflowInstanceService:
    """工作流实例服务"""

    @staticmethod
    def get_workflow_instance(
        db: Session, 
        instance_id: int, 
        current_user: models.User
    ) -> schemas.WorkflowInstance:
        """
        获取工作流实例详情
        """
        # 获取工作流实例
        instance = db.query(models.WorkflowInstance).filter(models.WorkflowInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == instance.ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="关联的台账不存在")
        
        # 检查用户是否有权限查看
        # if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        #     # 检查用户是否是审批人
        #     is_approver = False
            
        #     # 获取实例的所有节点
        #     instance_nodes = db.query(models.WorkflowInstanceNode).filter(
        #         models.WorkflowInstanceNode.workflow_instance_id == instance_id
        #     ).all()
            
        #     for node in instance_nodes:
        #         if node.approver_id == current_user.id:
        #             is_approver = True
        #             break
                
        #         # 检查用户是否在节点的审批人列表中
        #         workflow_node = db.query(models.WorkflowNode).filter(
        #             models.WorkflowNode.id == node.workflow_node_id
        #         ).first()
                
        #         if workflow_node:
        #             # 获取节点审批人
        #             approvers = db.query(models.User).join(
        #                 models.workflow_node_approvers,
        #                 models.workflow_node_approvers.c.user_id == models.User.id
        #             ).filter(
        #                 models.workflow_node_approvers.c.workflow_node_id == workflow_node.id
        #             ).all()
                    
        #             for approver in approvers:
        #                 if approver.id == current_user.id:
        #                     is_approver = True
        #                     break
                
        #         if is_approver:
        #             break
            
        #     if not is_approver:
        #         raise HTTPException(status_code=403, detail="无权查看此工作流实例")
        
        # 获取当前节点
        current_node = None
        if instance.current_node_id:
            current_node = db.query(models.WorkflowInstanceNode).filter(
                models.WorkflowInstanceNode.id == instance.current_node_id
            ).first()
            
            if current_node:
                # 获取节点定义
                workflow_node = db.query(models.WorkflowNode).filter(
                    models.WorkflowNode.id == current_node.workflow_node_id
                ).first()
                
                if workflow_node:
                    current_node.node_name = workflow_node.name
                    current_node.node_type = workflow_node.node_type
        
        # 获取所有节点
        instance_nodes = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.workflow_instance_id == instance_id
        ).all()
        
        # 将实例转换为schema
        instance_data = jsonable_encoder(instance)
        result = schemas.WorkflowInstance(**instance_data)
        result.nodes = instance_nodes
        result.current_node = current_node
        
        # 添加额外信息
        workflow = db.query(models.Workflow).filter(models.Workflow.id == instance.workflow_id).first()
        if workflow:
            result.workflow_name = workflow.name
        
        if ledger:
            result.ledger_name = ledger.name
        
        creator = db.query(models.User).filter(models.User.id == instance.created_by).first()
        if creator:
            # 使用deps中的转换方法获取schema格式的用户
            # result.creator = deps.convert_user_to_schema(creator)
            result.creator = creator
            result.creator_name = creator.name
        
        # 为每个节点添加节点定义信息
        for node in result.nodes:
            workflow_node = db.query(models.WorkflowNode).filter(
                models.WorkflowNode.id == node.workflow_node_id
            ).first()
            
            if workflow_node:
                node.node_name = workflow_node.name
                node.node_type = workflow_node.node_type
            
            # 添加审批人信息
            if node.approver_id:
                approver = db.query(models.User).filter(models.User.id == node.approver_id).first()
                if approver:
                    node.approver = approver
                    node.approver_name = approver.name
        
        return result

    @staticmethod
    def get_workflow_instance_by_ledger(
        db: Session, 
        ledger_id: int, 
        current_user: models.User
    ) -> schemas.WorkflowInstance:
        """
        获取台账的活动工作流实例
        """
        # 获取台账
        ledger = crud.ledger.get(db, id=ledger_id)
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 检查用户是否有权限查看
        # if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        #     # 检查用户是否在台账所属团队中
        #     if ledger.team_id:
        #         user_teams = [team.id for team in current_user.teams]
        #         if ledger.team_id not in user_teams:
        #             raise HTTPException(status_code=403, detail="无权查看此台账的工作流实例")
        #     else:
        #         raise HTTPException(status_code=403, detail="无权查看此台账的工作流实例")
        
        # 获取活动的工作流实例
        instance = crud.workflow_instance.get_by_ledger(db, ledger_id=ledger_id)
        if not instance:
            return None
        
        return WorkflowInstanceService.get_workflow_instance(db, instance.id, current_user)

    @staticmethod
    def get_workflow_instance_nodes(
        db: Session, 
        instance_id: int, 
        current_user: models.User
    ) -> List[schemas.WorkflowInstanceNode]:
        """
        获取工作流实例的所有节点
        """
        # 获取工作流实例
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 获取台账
        ledger = crud.ledger.get(db, id=instance.ledger_id)
        if not ledger:
            raise HTTPException(status_code=404, detail="关联的台账不存在")
        
        # 检查用户是否有权限查看
        # if not crud.user.is_superuser(current_user) and ledger.created_by_id != current_user.id:
        #     # 检查用户是否是审批人
        #     is_approver = False
            
        #     # 获取实例的所有节点
        #     instance_nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
        #     for node in instance_nodes:
        #         if node.approver_id == current_user.id:
        #             is_approver = True
        #             break
            
        #     if not is_approver:
        #         raise HTTPException(status_code=403, detail="无权查看此工作流实例的节点")
        
        # 获取所有节点
        nodes = crud.workflow_instance_node.get_by_instance(db, instance_id=instance_id)
        
        # 为每个节点添加节点定义信息
        for node in nodes:
            # 获取关联的工作流节点
            workflow_node_info = WorkflowNodeService.get_workflow_node(db, node.workflow_node_id)
            if workflow_node_info:
                node.node_name = workflow_node_info.get("name")
                node.node_type = workflow_node_info.get("node_type")
            
            # 添加审批人信息
            if node.approver_id:
                approver = db.query(models.User).filter(models.User.id == node.approver_id).first()
                if approver:
                    # node.approver = deps.convert_user_to_schema(approver)
                    node.approver = approver
                    node.approver_name = approver.name
        
        return nodes

    @staticmethod
    def approve_workflow_node(
        db: Session, 
        instance_id: int, 
        node_id: int, 
        approval_data: schemas.WorkflowNodeApproval, 
        current_user: models.User
    ) -> Dict[str, Any]:
        """
        审批通过工作流节点
        """
        # 获取工作流实例
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 检查工作流实例状态
        if instance.status != "active":
            raise HTTPException(status_code=400, detail="工作流实例已完成或已取消")
        
        # 检查节点是否是当前节点
        if instance.current_node_id != node_id:
            raise HTTPException(status_code=400, detail="只能审批当前节点")
        
        # 获取当前节点
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == node_id
        ).first()
        
        if not current_node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        # 获取工作流节点定义信息（使用WorkflowNodeService）
        workflow_node_info = WorkflowNodeService.get_workflow_node(db, current_node.workflow_node_id)
        if not workflow_node_info:
            raise HTTPException(status_code=400, detail="工作流节点不存在")
        
        # 检查用户是否有权限审批
        can_approve = False
        
        # 检查是否是指定的审批人
        if current_node.approver_id == current_user.id:
            can_approve = True
        
        # 检查是否在节点的审批人列表中
        if not can_approve:
            approver_ids = workflow_node_info.get("approver_ids", [])
            if current_user.id in approver_ids:
                can_approve = True
        
        # 检查是否具有节点指定的审批角色
        if not can_approve and workflow_node_info.get("approver_role_id"):
            # 获取用户角色
            user_roles = crud.user.get_user_roles(db, current_user.id)
            role = db.query(models.Role).filter(models.Role.id == workflow_node_info.get("approver_role_id")).first()
            if role and role.name in user_roles:
                can_approve = True
        
        # 超级管理员可以审批所有节点
        if not can_approve and not crud.user.is_superuser(current_user):
            raise HTTPException(status_code=403, detail="您没有权限审批此节点")
        
        # 审批节点
        result = crud.workflow_instance.approve_current_node(
            db,
            instance_id=instance_id,
            user_id=current_user.id,
            comment=approval_data.comment,
            next_approver_id=approval_data.next_approver_id if hasattr(approval_data, "next_approver_id") else None
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流完成，更新台账状态
        if result.get("workflow_completed"):
            ledger = crud.ledger.get(db, id=instance.ledger_id)
            if ledger:
                ledger.approval_status = "approved"
                ledger.approved_at = datetime.now()
                ledger.status = "completed"
                db.add(ledger)
                db.commit()
        
        return result

    @staticmethod
    def reject_workflow_node(
        db: Session, 
        instance_id: int, 
        node_id: int, 
        rejection_data: schemas.WorkflowNodeRejection, 
        current_user: models.User
    ) -> Dict[str, Any]:
        """
        拒绝工作流节点
        """
        # 获取工作流实例
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="工作流实例不存在")
        
        # 检查工作流实例状态
        if instance.status != "active":
            raise HTTPException(status_code=400, detail="工作流实例已完成或已取消")
        
        # 检查节点是否是当前节点
        if instance.current_node_id != node_id:
            raise HTTPException(status_code=400, detail="只能拒绝当前节点")
        
        # 获取当前节点
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == node_id
        ).first()
        
        if not current_node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        # 获取工作流节点定义信息（使用WorkflowNodeService）
        workflow_node_info = WorkflowNodeService.get_workflow_node(db, current_node.workflow_node_id)
        if not workflow_node_info:
            raise HTTPException(status_code=400, detail="工作流节点不存在")
        
        # 检查用户是否有权限拒绝
        can_reject = False
        
        # 检查是否是指定的审批人
        if current_node.approver_id == current_user.id:
            can_reject = True
        
        # 检查是否在节点的审批人列表中
        if not can_reject:
            approver_ids = workflow_node_info.get("approver_ids", [])
            if current_user.id in approver_ids:
                can_reject = True
        
        # 检查是否具有节点指定的审批角色
        if not can_reject and workflow_node_info.get("approver_role_id"):
            # 获取用户角色
            user_roles = crud.user.get_user_roles(db, current_user.id)
            role = db.query(models.Role).filter(models.Role.id == workflow_node_info.get("approver_role_id")).first()
            if role and role.name in user_roles:
                can_reject = True
        
        # 超级管理员可以拒绝所有节点
        if not can_reject and not crud.user.is_superuser(current_user):
            raise HTTPException(status_code=403, detail="您没有权限拒绝此节点")
        
        # 拒绝节点
        result = crud.workflow_instance.reject_current_node(
            db,
            instance_id=instance_id,
            user_id=current_user.id,
            comment=rejection_data.comment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 如果工作流被拒绝，更新台账状态
        if result.get("workflow_rejected"):
            ledger = crud.ledger.get(db, id=instance.ledger_id)
            if ledger:
                ledger.approval_status = "rejected"
                ledger.status = "returned"
                db.add(ledger)
                db.commit()
        
        return result


workflow_instance_service = WorkflowInstanceService() 