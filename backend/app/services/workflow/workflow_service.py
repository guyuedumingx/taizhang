from typing import Any, List, Optional, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.utils.logger import LoggerService

class WorkflowService:
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
            for workflow in workflows:
                try:
                    # 获取创建者和更新者信息
                    if workflow.created_by:
                        creator = db.query(models.User).filter(models.User.id == workflow.created_by).first()
                        workflow.creator_name = creator.name if creator else None
                    
                    # 获取节点数量
                    workflow.node_count = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).count()
                except Exception as e:
                    print(f"处理工作流 {workflow.id} 的信息时出错: {e}")
                    workflow.creator_name = None
                    workflow.node_count = 0
                workflow.creator = None
            
            # 将ORM模型转换为Pydantic模型
            from fastapi.encoders import jsonable_encoder
            pydantic_workflows = []
            for workflow in workflows:
                try:
                    # 先转为JSON，再转为Pydantic模型，避免循环引用问题
                    workflow_dict = jsonable_encoder(workflow)
                    pydantic_workflow = schemas.Workflow.parse_obj(workflow_dict)
                    pydantic_workflows.append(pydantic_workflow)
                except Exception as e:
                    print(f"转换工作流 {workflow.id} 到Pydantic模型时出错: {e}")
            
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
                    reject_to_node_id=node_data.reject_to_node_id,
                )
                db.add(node)
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
        
        # 获取创建者信息
        if workflow.created_by:
            creator = db.query(models.User).filter(models.User.id == workflow.created_by).first()
            workflow.creator_name = creator.name if creator else None
        
        # 获取节点数量
        workflow.node_count = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).count()
        
        # 将ORM模型转换为Pydantic模型
        from fastapi.encoders import jsonable_encoder
        try:
            # 先转为JSON，再转为Pydantic模型，避免循环引用问题
            workflow_dict = jsonable_encoder(workflow)
            pydantic_workflow = schemas.Workflow.parse_obj(workflow_dict)
            return pydantic_workflow
        except Exception as e:
            print(f"转换工作流到Pydantic模型时出错: {e}")
            raise HTTPException(status_code=500, detail="系统内部错误")
    
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
            workflow.creator_name = creator.name if creator else None
        
        # 获取节点
        nodes = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).order_by(models.WorkflowNode.order_index).all()
        workflow.nodes = nodes
        
        # 将ORM模型转换为Pydantic模型
        from fastapi.encoders import jsonable_encoder
        try:
            # 先转为JSON，再转为Pydantic模型，避免循环引用问题
            workflow_dict = jsonable_encoder(workflow)
            pydantic_workflow = schemas.Workflow.parse_obj(workflow_dict)
            return pydantic_workflow
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
        
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # 处理节点更新
        if hasattr(workflow_in, "nodes") and workflow_in.nodes is not None:
            # 删除现有节点
            db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).delete()
            db.commit()
            
            # 创建新节点
            for node_data in workflow_in.nodes:
                node = models.WorkflowNode(
                    name=node_data.name,
                    description=node_data.description,
                    workflow_id=workflow.id,
                    node_type=node_data.node_type,
                    order_index=node_data.order_index,
                    reject_to_node_id=node_data.reject_to_node_id,
                )
                db.add(node)
            db.commit()
        
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
        
        
        if workflow.created_by:
            creator = db.query(models.User).filter(models.User.id == workflow.created_by).first()
            workflow.creator_name = creator.name if creator else None
        
        # 获取节点
        nodes = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).order_by(models.WorkflowNode.order_index).all()
        workflow.nodes = nodes
        
        # 将ORM模型转换为Pydantic模型
        from fastapi.encoders import jsonable_encoder
        try:
            workflow_dict = jsonable_encoder(workflow)
            pydantic_workflow = schemas.Workflow.parse_obj(workflow_dict)
            return pydantic_workflow
        except Exception as e:
            print(f"转换工作流到Pydantic模型时出错: {e}")
            raise HTTPException(status_code=500, detail="系统内部错误")
    
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
        
        # 检查是否有关联的台账
        ledgers = db.query(models.Ledger).filter(models.Ledger.workflow_id == workflow_id).count()
        if ledgers > 0:
            raise HTTPException(status_code=400, detail="该工作流已被台账使用，无法删除")
        
        # 检查是否有关联的模板 - 现在模板关联工作流，所以需要检查
        templates = db.query(models.Template).filter(models.Template.workflow_id == workflow_id).count()
        if templates > 0:
            raise HTTPException(status_code=400, detail="该工作流已被模板使用，请先解除关联")
        
        # 删除节点
        db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow.id).delete()
        
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
        
        # 创建用于返回的工作流副本
        from fastapi.encoders import jsonable_encoder
        try:
            # 首先尝试转换为Pydantic模型
            workflow_dict = jsonable_encoder(workflow)
            pydantic_workflow = schemas.Workflow.parse_obj(workflow_dict)
            
            # 然后删除原工作流
            db.delete(workflow)
            db.commit()
            
            return pydantic_workflow
        except Exception as e:
            print(f"转换工作流到Pydantic模型时出错: {e}")
            
            # 如果转换失败，仍然删除工作流，但返回None
            db.delete(workflow)
            db.commit()
            
            return None
    
    @staticmethod
    def get_workflow_nodes(db: Session, workflow_id: int) -> List[schemas.WorkflowNode]:
        """
        获取工作流节点列表
        """
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        nodes = db.query(models.WorkflowNode).filter(models.WorkflowNode.workflow_id == workflow_id).order_by(models.WorkflowNode.order_index).all()
        
        # 将ORM模型转换为Pydantic模型
        from fastapi.encoders import jsonable_encoder
        try:
            # 先转为JSON，再转为Pydantic模型，避免循环引用问题
            node_dicts = jsonable_encoder(nodes)
            pydantic_nodes = [schemas.WorkflowNode.parse_obj(node_dict) for node_dict in node_dicts]
            return pydantic_nodes
        except Exception as e:
            print(f"转换工作流节点到Pydantic模型时出错: {e}")
            raise HTTPException(status_code=500, detail="系统内部错误")

workflow_service = WorkflowService() 