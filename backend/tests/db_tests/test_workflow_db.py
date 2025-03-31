import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app import crud, models, schemas


def test_create_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试创建工作流"""
    # 首先创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    # 然后创建模板并关联到工作流
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow.id,
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    assert workflow.name == test_workflow["name"]
    assert workflow.description == test_workflow["description"]
    assert workflow.is_active == test_workflow["is_active"]
    assert template.workflow_id == workflow.id
    assert workflow.created_by == 1


def test_get_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试获取工作流"""
    # 首先创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    # 然后创建模板并关联到工作流
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=created_workflow.id,
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    fetched_workflow = crud.workflow.get(db, id=created_workflow.id)
    
    assert fetched_workflow
    assert fetched_workflow.id == created_workflow.id
    assert fetched_workflow.name == test_workflow["name"]
    assert fetched_workflow.description == test_workflow["description"]
    assert template.workflow_id == fetched_workflow.id


def test_get_workflow_by_name(db: Session, test_workflow: dict, test_template: dict):
    """测试通过名称获取工作流"""
    # 首先创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    # 然后创建模板并关联到工作流
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=created_workflow.id,
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    workflow = db.query(models.Workflow).filter(models.Workflow.name == test_workflow["name"]).first()
    
    assert workflow is not None
    assert workflow.name == test_workflow["name"]
    assert workflow.description == test_workflow["description"]
    assert template.workflow_id == workflow.id


def test_update_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试更新工作流"""
    # 首先创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    # 然后创建模板并关联到工作流
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=created_workflow.id,
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    # 直接更新字段
    created_workflow.description = "Updated workflow description"
    created_workflow.is_active = False
    db.add(created_workflow)
    db.commit()
    db.refresh(created_workflow)
    
    # 确认更新成功
    assert created_workflow.description == "Updated workflow description"
    assert created_workflow.is_active == False
    assert template.workflow_id == created_workflow.id


def test_delete_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试删除工作流"""
    # 首先创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    created_workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    workflow_id = created_workflow.id
    
    # 然后创建模板并关联到工作流
    template_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow_id,
        fields=[]
    )
    template = crud.template.create(db, obj_in=template_in, creator_id=1)
    
    deleted_workflow = crud.workflow.remove(db, id=workflow_id)
    
    assert deleted_workflow.id == workflow_id
    
    # 确认工作流已被删除
    fetched_workflow = crud.workflow.get(db, id=workflow_id)
    assert fetched_workflow is None


def test_get_multi_workflows(db: Session, test_workflow: dict, test_template: dict):
    """测试获取多个工作流"""
    # 创建第一个工作流
    workflow1_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=test_workflow["is_active"],
        nodes=[]
    )
    
    # 创建第二个工作流
    workflow2_in = schemas.WorkflowCreate(
        name=f"{test_workflow['name']}_2",
        description=f"{test_workflow['description']} 2",
        is_active=False,
        nodes=[]
    )
    
    workflow1 = crud.workflow.create_with_nodes(db, obj_in=workflow1_in, created_by=1)
    workflow2 = crud.workflow.create_with_nodes(db, obj_in=workflow2_in, created_by=1)
    
    # 创建模板并关联到两个工作流
    template1_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow1.id,
        fields=[]
    )
    template2_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow2.id,
        fields=[]
    )
    
    crud.template.create(db, obj_in=template1_in, creator_id=1)
    crud.template.create(db, obj_in=template2_in, creator_id=1)
    
    workflows = crud.workflow.get_multi(db)
    
    assert len(workflows) == 2
    assert any(w.name == test_workflow["name"] for w in workflows)
    assert any(w.name == f"{test_workflow['name']}_2" for w in workflows)


def test_get_active_workflows(db: Session, test_workflow: dict, test_template: dict):
    """测试获取激活的工作流"""
    # 创建激活的工作流
    workflow1_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=True,
        nodes=[]
    )
    
    # 创建非激活的工作流
    workflow2_in = schemas.WorkflowCreate(
        name=f"{test_workflow['name']}_2",
        description=f"{test_workflow['description']} 2",
        is_active=False,
        nodes=[]
    )
    
    workflow1 = crud.workflow.create_with_nodes(db, obj_in=workflow1_in, created_by=1)
    workflow2 = crud.workflow.create_with_nodes(db, obj_in=workflow2_in, created_by=1)
    
    # 创建模板并关联到两个工作流
    template1_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow1.id,
        fields=[]
    )
    template2_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow2.id,
        fields=[]
    )
    
    crud.template.create(db, obj_in=template1_in, creator_id=1)
    crud.template.create(db, obj_in=template2_in, creator_id=1)
    
    # 获取激活的工作流
    active_workflows = db.query(models.Workflow).filter(models.Workflow.is_active == True).all()
    
    assert len(active_workflows) == 1
    assert active_workflows[0].name == test_workflow["name"]
    assert active_workflows[0].is_active == True


def test_get_templates_by_workflow(db: Session, test_workflow: dict, test_template: dict):
    """测试获取工作流关联的模板"""
    # 创建工作流
    workflow_in = schemas.WorkflowCreate(
        name=test_workflow["name"],
        description=test_workflow["description"],
        is_active=True,
        nodes=[]
    )
    
    workflow = crud.workflow.create_with_nodes(db, obj_in=workflow_in, created_by=1)
    
    # 创建多个关联到同一工作流的模板
    template1_in = schemas.TemplateCreate(
        name=test_template["name"],
        description=test_template["description"],
        is_system=test_template["is_system"],
        department="测试部门",
        workflow_id=workflow.id,
        fields=[]
    )
    template2_in = schemas.TemplateCreate(
        name=f"{test_template['name']}_2",
        description=f"{test_template['description']} 2",
        is_system=test_template["is_system"],
        department="测试部门2",
        workflow_id=workflow.id,
        fields=[]
    )
    
    crud.template.create(db, obj_in=template1_in, creator_id=1)
    crud.template.create(db, obj_in=template2_in, creator_id=1)
    
    # 获取与工作流关联的模板
    workflow_templates = db.query(models.Template).filter(models.Template.workflow_id == workflow.id).all()
    
    assert len(workflow_templates) == 2
    assert any(t.name == test_template["name"] for t in workflow_templates)
    assert any(t.name == f"{test_template['name']}_2" for t in workflow_templates) 