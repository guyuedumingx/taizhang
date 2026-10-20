from typing import Any, List, Optional, Dict
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from fastapi.encoders import jsonable_encoder
import time
import logging

from app import crud, models, schemas
from app.utils.logger import LoggerService, log_audit
from app.api import deps
from app.services.workflow_node_service import WorkflowNodeService
from app.services.workflow_hooks import run_completion_hooks, run_rejection_hooks

# 性能分析日志记录器
perf_logger = logging.getLogger("taizhang.performance")



def _user_can_act_on_node(
    db: Session,
    current_node,
    workflow_node_info: dict,
    current_user: models.User,
) -> bool:
    """审批人判定 (Phase 2: 原先 approve/reject 各抄一份, 逐字雷同):
    指定审批人 -> 节点审批人名单 -> 节点角色 -> 超级管理员。"""
    if current_node.approver_id == current_user.id:
        return True
    if current_user.id in workflow_node_info.get("approver_ids", []):
        return True
    if workflow_node_info.get("approver_role_id"):
        user_roles = crud.user.get_user_roles(db, current_user.id)
        role = db.query(models.Role).filter(
            models.Role.id == workflow_node_info.get("approver_role_id")
        ).first()
        if role and role.name in user_roles:
            return True
    return crud.user.is_superuser(current_user)


class WorkflowInstanceService:
    """工作流实例服务"""

    @staticmethod
    def get_workflow_instances_by_ledger_ids(
        db: Session,
        ledger_ids: List[int],
        *,
        include_nodes: bool = False,
        include_creator: bool = False,
        include_workflow: bool = True,
    ) -> Dict[int, schemas.WorkflowInstance]:
        """
        批量获取指定台账的工作流实例，避免逐条查询导致的N+1问题。
        针对列表页优化：只加载必要字段，不加载节点详情。
        返回字典，key为ledger_id，value为WorkflowInstance schema对象。
        """
        if not ledger_ids:
            return {}

        total_start = time.perf_counter()
        step_times = {}

        # 步骤1: 构建查询（只查询必要字段）
        step_start = time.perf_counter()
        # 使用更高效的查询方式：只选择需要的列
        query = db.query(
            models.WorkflowInstance.id,
            models.WorkflowInstance.workflow_id,
            models.WorkflowInstance.ledger_id,
            models.WorkflowInstance.status,
            models.WorkflowInstance.current_node_id,
            models.WorkflowInstance.created_by,
            models.WorkflowInstance.created_at,
            models.WorkflowInstance.updated_at,
            models.WorkflowInstance.completed_at,
        ).filter(
            models.WorkflowInstance.ledger_id.in_(ledger_ids)
        )
        step_times["1_构建查询"] = (time.perf_counter() - step_start) * 1000

        # 步骤2: 执行查询（不使用预加载，直接查询）
        step_start = time.perf_counter()
        instances = query.all()
        instance_count = len(instances)
        step_times["2_执行查询"] = (time.perf_counter() - step_start) * 1000

        # 步骤3: 批量获取工作流名称（如果需要）
        step_start = time.perf_counter()
        workflow_names = {}
        if include_workflow and instances:
            workflow_ids = {inst.workflow_id for inst in instances if inst.workflow_id}
            if workflow_ids:
                # 只查询id和name，减少数据传输
                workflows = db.query(models.Workflow.id, models.Workflow.name).filter(
                    models.Workflow.id.in_(workflow_ids)
                ).all()
                workflow_names = {w.id: w.name for w in workflows}
        step_times["3_批量获取工作流名称"] = (time.perf_counter() - step_start) * 1000

        # 步骤4: 批量获取创建人名称（如果需要）
        step_start = time.perf_counter()
        creator_names = {}
        if include_creator and instances:
            creator_ids = {inst.created_by for inst in instances if inst.created_by}
            if creator_ids:
                # 只查询id和name
                creators = db.query(models.User.id, models.User.name).filter(
                    models.User.id.in_(creator_ids)
                ).all()
                creator_names = {c.id: c.name for c in creators}
        step_times["4_批量获取创建人名称"] = (time.perf_counter() - step_start) * 1000

        # 步骤5: 快速数据转换
        step_start = time.perf_counter()
        result: Dict[int, schemas.WorkflowInstance] = {}

        for instance in instances:
            # 直接构建schema对象，使用最小字段集
            instance_schema = schemas.WorkflowInstance(
                id=instance.id,
                workflow_id=instance.workflow_id,
                ledger_id=instance.ledger_id,
                status=instance.status,
                current_node_id=instance.current_node_id,
                created_by=instance.created_by,
                created_at=instance.created_at,
                updated_at=instance.updated_at,
                completed_at=instance.completed_at,
                workflow_name=workflow_names.get(instance.workflow_id) if include_workflow else None,
                creator_name=creator_names.get(instance.created_by) if include_creator else None,
                nodes=[],  # 列表页不需要节点
                current_node=None,  # 列表页不需要当前节点详情
            )

            result[instance.ledger_id] = instance_schema
        step_times["5_处理数据转换"] = (time.perf_counter() - step_start) * 1000

        total_time = (time.perf_counter() - total_start) * 1000

        # 输出性能日志
        perf_logger.info(
            f"[工作流实例批量加载] 参数: ledger_ids数量={len(ledger_ids)}, "
            f"include_nodes={include_nodes}, include_creator={include_creator}, "
            f"include_workflow={include_workflow}, 返回实例数={instance_count}"
        )
        perf_logger.info(
            f"[工作流实例批量加载] 各步骤耗时(ms): "
            f"1_构建查询={step_times.get('1_构建查询', 0):.2f}, "
            f"2_执行查询={step_times.get('2_执行查询', 0):.2f}, "
            f"3_批量获取工作流名称={step_times.get('3_批量获取工作流名称', 0):.2f}, "
            f"4_批量获取创建人名称={step_times.get('4_批量获取创建人名称', 0):.2f}, "
            f"5_处理数据转换={step_times.get('5_处理数据转换', 0):.2f}"
        )
        perf_logger.info(
            f"[工作流实例批量加载] 总耗时={total_time:.2f}ms, "
            f"平均每个实例={total_time/instance_count if instance_count > 0 else 0:.2f}ms, "
            f"查询命中率={instance_count/len(ledger_ids)*100 if ledger_ids else 0:.1f}%"
        )

        return result

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
        
        # 权限判定 (Phase 2: 与 reject 共用 helper)
        if not _user_can_act_on_node(db, current_node, workflow_node_info, current_user):
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
        
        # Phase 2: 完成后的业务回写走回调注册表 (台账回调见 workflow_hooks.py)
        if result.get("workflow_completed"):
            run_completion_hooks(db, instance)
        
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
        
        # 权限判定 (Phase 2: 与 approve 共用 helper)
        if not _user_can_act_on_node(db, current_node, workflow_node_info, current_user):
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
        
        # Phase 2: 驳回后的业务回写走回调注册表
        if result.get("workflow_rejected"):
            run_rejection_hooks(db, instance)
        
        return result


workflow_instance_service = WorkflowInstanceService() 