import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app import crud, models, schemas


def test_create_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试创建工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    assert workflow.name == test_workflow["name"]
    assert workflow.description == test_workflow["description"]
    assert workflow.is_active == test_workflow["is_active"]
    assert workflow.template_id == template.id
    assert workflow.created_by == 1


def test_get_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试获取工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    fetched_workflow = crud.workflow.get(db, id=created_workflow.id)
    
    assert fetched_workflow
    assert fetched_workflow.id == created_workflow.id
    assert fetched_workflow.name == test_workflow["name"]
    assert fetched_workflow.description == test_workflow["description"]
    assert fetched_workflow.template_id == template.id


def test_get_workflow_by_name(db: Session, test_workflow: dict, test_template: dict):
    """测试通过名称获取工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    workflow = db.query(models.Workflow).filter(models.Workflow.name == test_workflow["name"]).first()
    
    assert workflow is not None
    assert workflow.name == test_workflow["name"]
    assert workflow.description == test_workflow["description"]
    assert workflow.template_id == template.id


def test_update_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试更新工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    new_description = "Updated workflow description"
    new_is_active = False
    
    workflow_update = schemas.WorkflowUpdate(
        description=new_description,
        is_active=new_is_active,
    )
    
    updated_workflow = crud.workflow.update_with_nodes(db, db_obj=created_workflow, obj_in=workflow_update)
    
    assert updated_workflow.id == created_workflow.id
    assert updated_workflow.name == test_workflow["name"]  # 名称未更新
    assert updated_workflow.description == new_description
    assert updated_workflow.is_active == new_is_active
    assert updated_workflow.template_id == template.id


def test_delete_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试删除工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    workflow_id = created_workflow.id
    
    deleted_workflow = crud.workflow.remove(db, id=workflow_id)
    
    assert deleted_workflow.id == workflow_id
    
    # 确认工作流已被删除
    fetched_workflow = crud.workflow.get(db, id=workflow_id)
    assert fetched_workflow is None


def test_get_multi_workflows(db: Session, test_workflow: dict, test_template: dict):
    """测试获取多个工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建第一个工作流
    workflow1_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        template_id=template.id,
        nodes=[]
    )
    
    # 创建第二个工作流
    workflow2_in = schemas.WorkflowCreate(
        name=f"{test_workflow['name']}_2",
        description=f"{test_workflow['description']} 2",
        is_active=False,
        template_id=template.id,
        nodes=[]
    )
    
    crud.workflow.create_with_nodes(db, obj_in=workflow1_in, created_by=1)
    crud.workflow.create_with_nodes(db, obj_in=workflow2_in, created_by=1)
    
    workflows = crud.workflow.get_multi(db)
    
    assert len(workflows) == 2
    assert any(w.name == test_workflow["name"] for w in workflows)
    assert any(w.name == f"{test_workflow['name']}_2" for w in workflows)


def test_get_active_workflows(db: Session, test_workflow: dict, test_template: dict):
    """测试获取激活的工作流"""
    # 创建模板
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 创建激活的工作流
    workflow1_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=True,
        template_id=template.id,
        nodes=[]
    )
    
    # 创建非激活的工作流
    workflow2_in = schemas.WorkflowCreate(
        name=f"{test_workflow['name']}_2",
        description=f"{test_workflow['description']} 2",
        is_active=False,
        template_id=template.id,
        nodes=[]
    )
    
    crud.workflow.create_with_nodes(db, obj_in=workflow1_in, created_by=1)
    crud.workflow.create_with_nodes(db, obj_in=workflow2_in, created_by=1)
    
    # 获取激活的工作流
    active_workflows = db.query(models.Workflow).filter(models.Workflow.is_active == True).all()
    
    assert len(active_workflows) == 1
    assert active_workflows[0].name == test_workflow["name"]
    assert active_workflows[0].is_active == True
    assert active_workflows[0].template_id == template.id 