from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from fastapi.encoders import jsonable_encoder

from app import models, schemas
from app.utils.logger import LoggerService
from app.api import deps
from app.services.workflow_node_service import WorkflowNodeService

class WorkflowService:
    @staticmethod
    def _orm_to_dict(obj):
        """
        将SQLAlchemy ORM对象转换为纯字典，只包含模型的属性字段
        避免循环引用和非可序列化对象
        """
        if obj is None:
            return None
            
        # 使用SQLAlchemy inspect获取所有属性
        mapper = inspect(obj).mapper
        result = {}
        
        # 遍历所有列字段
        for column in mapper.columns:
            attr_name = column.key
            result[attr_name] = getattr(obj, attr_name)
            
        # 添加额外的属性
        if hasattr(obj, "creator_name"):
            result["creator_name"] = obj.creator_name
        if hasattr(obj, "node_count"):
            result["node_count"] = obj.node_count
            
        return result
    
    @staticmethod
    def _get_node_approvers(db: Session, node_id: int) -> List[Dict]:
        """
        直接使用SQL查询获取节点的审批人列表，避免ORM循环引用问题
        """
        query = text("""
            SELECT u.id, u.name, u.username, u.ehr_id, u.is_active
            FROM users u
            JOIN workflow_node_approvers wna ON u.id = wna.user_id
            WHERE wna.workflow_node_id = :node_id
        """)
        
        result = db.execute(query, {"node_id": node_id}).fetchall()
        
        approvers = []
        for row in result:
            approver = {
                "id": row[0],
                "name": row[1],
                "username": row[2] if row[2] else None,
                "ehr_id": row[3] if row[3] else None,
                "is_active": row[4] if row[4] else True
            }
            approvers.append(approver)
            
        return approvers
    
    @staticmethod
    def get_workflows(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[schemas.Workflow]:
        """
        获取工作流列表
        """
        try:
            # 构建查询
            query = db.query(models.Workflow)
            
            # 搜索
            if search:
                query = query.filter(models.Workflow.name.ilike(f"%{search}%"))
            
            # 分页
            workflows = query.offset(skip).limit(limit).all()
            
            # 获取关联信息
            pydantic_workflows = []
            for workflow in workflows:
                try:
                    # 获取创建者和更新者信息
                    if workflow.created_by:
                        creator = db.query(models.User).filter(models.User.id == workflow.created_by).first()
                        if creator:
                            # workflow.creator = deps.convert_user_to_schema(creator)
                            workflow.creator = creator
                            workflow.creator_name = creator.name
                    
                    # 获取节点数量
                    workflow.node_count = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).count()
                    
                    # 转换为Pydantic模型
                    workflow_dict = jsonable_encoder(workflow)
                    pydantic_workflow = schemas.Workflow.model_validate(workflow_dict)
                    pydantic_workflows.append(pydantic_workflow)
                except Exception as e:
                    print(f"处理工作流 {workflow.id} 的信息时出错: {e}")
            
            return pydantic_workflows
        except Exception as e:
            print(f"获取工作流列表时出错: {e}")
            return []
    
    @staticmethod
    def create_workflow(
        db: Session,
        workflow_in: schemas.WorkflowCreate,
        current_user_id: int
    ) -> schemas.Workflow:
        """
        创建新工作流
        """
        # 检查工作流名称是否已存在
        workflow = db.query(models.Workflow).filter(models.Workflow.name == workflow_in.name).first()
        if workflow:
            raise HTTPException(
                status_code=400,
                detail="工作流名称已存在",
            )
        
        # 创建工作流 - 不再设置template_id
        workflow = models.Workflow(
            name=workflow_in.name,
            description=workflow_in.description,
            created_by=current_user_id,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # 创建节点
        if workflow_in.nodes:
            for node_data in workflow_in.nodes:
                node = models.WorkflowNode(
                    name=node_data.name,
                    description=node_data.description,
                    workflow_id=workflow.id,
                    node_type=node_data.node_type,
                    order_index=node_data.order_index,
                    approver_role_id=node_data.approver_role_id,
                    multi_approve_type=node_data.multi_approve_type,
                    reject_to_node_id=node_data.reject_to_node_id,
                )
                db.add(node)
                db.flush()  # 获取数据库分配的ID
                
                # 处理审批人列表
                if hasattr(node_data, 'approver_ids') and node_data.approver_ids:
                    WorkflowNodeService.update_node_approvers(db, node.id, node_data.approver_ids)
                
            db.commit()
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            user_id=current_user_id,
            module="workflow",
            action="create_workflow",
            resource_id=str(workflow.id),
            resource_type="workflow",
            message=f"创建工作流: {workflow.name}"
        )
        
        # 获取完整的工作流（包含所有相关信息）
        return WorkflowService.get_workflow(db, workflow.id)
    
    @staticmethod
    def get_workflow(db: Session, workflow_id: int) -> schemas.Workflow:
        """
        获取工作流详情
        """
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 获取创建者信息
        if workflow.created_by:
            creator = db.query(models.User).filter(models.User.id == workflow.created_by).first()
            if creator:
                # 使用转换方法获取schema格式的用户
                workflow.creator = creator
                # workflow.creator = deps.convert_user_to_schema(creator)
                workflow.creator_name = creator.name
            else:
                workflow.creator = None
                workflow.creator_name = None
        
        # 手动获取节点，通过WorkflowNodeService
        nodes = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).order_by(models.WorkflowNode.order_index).all()
        
        # 获取每个节点的完整信息
        nodes_info = []
        for node in nodes:
            # 使用node service获取完整节点信息
            node_info = WorkflowNodeService.get_workflow_node(db, node.id)
            nodes_info.append(node_info)
        
        # 转换工作流为Pydantic模型
        workflow_dict = jsonable_encoder(workflow)
        workflow_dict["nodes"] = nodes_info
        workflow_dict["node_count"] = len(nodes_info)
        
        try:
            return schemas.Workflow.model_validate(workflow_dict)
        except Exception as e:
            print(f"转换工作流到Pydantic模型时出错: {e}")
            raise HTTPException(status_code=500, detail="系统内部错误")
    
    @staticmethod
    def update_workflow(
        db: Session,
        workflow_id: int,
        workflow_in: schemas.WorkflowUpdate,
        current_user_id: int
    ) -> schemas.Workflow:
        """
        更新工作流信息
        """
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 如果更新工作流名称，检查是否已存在
        if workflow_in.name and workflow_in.name != workflow.name:
            existing_workflow = db.query(models.Workflow).filter(models.Workflow.name == workflow_in.name).first()
            if existing_workflow:
                raise HTTPException(
                    status_code=400,
                    detail="工作流名称已存在",
                )
        
        # 更新工作流信息
        try:
            # 尝试新API
            update_data = workflow_in.model_dump(exclude_unset=True, exclude={"nodes"})
        except AttributeError:
            # 老版本Pydantic
            update_data = workflow_in.dict(exclude_unset=True, exclude={"nodes"})
        
        # 更新其他字段
        for field, value in update_data.items():
            if field != 'template_id':
                setattr(workflow, field, value)
        
        # 更新节点
        if workflow_in.nodes:
            # 首先删除所有现有节点
            db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow_id).delete()
            db.commit()
            
            # 创建新节点，暂时不处理reject_to_node_id
            created_nodes = []
            node_id_map = {}  # 用于存储临时ID与实际数据库ID的映射
            
            for i, node_data in enumerate(workflow_in.nodes):
                node = models.WorkflowNode(
                    name=node_data.name,
                    description=node_data.description,
                    workflow_id=workflow_id,
                    node_type=node_data.node_type,
                    order_index=node_data.order_index,
                    approver_role_id=node_data.approver_role_id,
                    multi_approve_type=node_data.multi_approve_type,
                    reject_to_node_id=None  # 先设为None，稍后更新
                )
                db.add(node)
                db.flush()  # 获取数据库分配的ID
                
                # 记录临时ID或索引与实际数据库ID的映射
                if hasattr(node_data, 'id') and node_data.id:
                    node_id_map[node_data.id] = node.id
                else:
                    # 使用索引作为临时ID
                    node_id_map[i] = node.id
                
                # 处理审批人列表（使用WorkflowNodeService）
                if hasattr(node_data, 'approver_ids') and node_data.approver_ids:
                    WorkflowNodeService.update_node_approvers(db, node.id, node_data.approver_ids)
                
                created_nodes.append((node, node_data))
            
            # 第二遍：更新reject_to_node_id
            for node, node_data in created_nodes:
                if node_data.reject_to_node_id is not None:
                    # 尝试从映射中获取实际的reject_to_node_id
                    if node_data.reject_to_node_id in node_id_map:
                        node.reject_to_node_id = node_id_map[node_data.reject_to_node_id]
                        db.add(node)
        
        # 保存更新
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            user_id=current_user_id,
            module="workflow",
            action="update_workflow",
            resource_id=str(workflow.id),
            resource_type="workflow",
            message=f"更新工作流: {workflow.name}"
        )
        
        # 获取完整的工作流（包含所有相关信息）
        return WorkflowService.get_workflow(db, workflow.id)
    
    @staticmethod
    def delete_workflow(
        db: Session, 
        workflow_id: int,
        current_user_id: int
    ) -> schemas.Workflow:
        """
        删除工作流
        """
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 检查是否有关联的模板 - 现在模板关联工作流，所以需要检查
        templates = db.query(models.Template).filter(models.Template.workflow_id == workflow_id).count()
        if templates > 0:
            raise HTTPException(status_code=400, detail="该工作流已被模板使用，请先解除关联")
        
        # 创建工作流副本用于返回
        workflow_dict = jsonable_encoder(workflow)
        workflow_dict["node_count"] = 0
        workflow_dict["nodes"] = []
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            user_id=current_user_id,
            module="workflow",
            action="delete_workflow",
            resource_id=str(workflow.id),
            resource_type="workflow",
            message=f"删除工作流: {workflow.name}"
        )
        
        # 删除节点
        db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).delete()
        
        # 删除工作流
        db.delete(workflow)
        db.commit()
        
        # 转换为Pydantic模型返回
        try:
            pydantic_workflow = schemas.Workflow.model_validate(workflow_dict)
            return pydantic_workflow
        except Exception as e:
            print(f"转换工作流到Pydantic模型时出错: {e}")
            return None
    
    @staticmethod
    def get_workflow_nodes(db: Session, workflow_id: int) -> List[schemas.WorkflowNode]:
        """
        获取工作流节点列表
        """
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 查询所有节点ID
        node_ids = db.query(models.WorkflowNode.id).filter(
            models.WorkflowNode.workflow_id == workflow_id
        ).order_by(models.WorkflowNode.order_index).all()
        
        # 获取每个节点的完整信息
        nodes = []
        for (node_id,) in node_ids:
            # 使用WorkflowNodeService获取节点详情
            node_info = WorkflowNodeService.get_workflow_node(db, node_id)
            # 将字典转换为Pydantic模型
            try:
                node_model = schemas.WorkflowNode.model_validate(node_info)
                nodes.append(node_model)
            except Exception as e:
                print(f"转换节点到Pydantic模型时出错: {e}")
        
        return nodes

workflow_service = WorkflowService() 