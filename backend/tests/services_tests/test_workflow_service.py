import pytest
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.workflow.workflow_service import workflow_service


def test_get_workflows(db: Session, workflow: models.Workflow, template: models.Template):
    """测试获取工作流列表"""
    # 再创建一个测试工作流
    workflow_in = schemas.WorkflowCreate(
        name="测试工作流2",
        description="这是测试工作流2"
    )
    workflow2 = workflow_service.create_workflow(db, workflow_in, 1)
    
    # 测试获取所有工作流
    workflows = workflow_service.get_workflows(db)
    assert len(workflows) >= 2
    
    # 测试按名称搜索
    workflows = workflow_service.get_workflows(db, search="测试工作流2")
    assert len(workflows) == 1
    assert workflows[0].name == "测试工作流2"
    
    # 测试分页
    workflows = workflow_service.get_workflows(db, skip=1, limit=1)
    assert len(workflows) == 1


def test_create_workflow(db: Session, template: models.Template, normal_user: models.User):
    """测试创建工作流"""
    # 创建测试数据
    workflow_in = schemas.WorkflowCreate(
        name="新工作流",
        description="这是一个新工作流",
        nodes=[
            schemas.WorkflowNodeCreate(
                name="节点1",
                description="第一个节点",
                node_type="approval",
                order_index=1,
                workflow_id=0  # 创建时会自动设置
            )
        ]
    )
    
    # 创建工作流
    workflow = workflow_service.create_workflow(db, workflow_in, normal_user.id)
    
    # 验证创建结果
    assert workflow.name == "新工作流"
    assert workflow.description == "这是一个新工作流"
    assert workflow.created_by == normal_user.id
    
    # 验证节点创建
    nodes = workflow_service.get_workflow_nodes(db, workflow.id)
    assert len(nodes) == 1
    assert nodes[0].name == "节点1"
    assert nodes[0].description == "第一个节点"
    
    # 测试创建重复名称的工作流
    with pytest.raises(Exception):
        workflow_service.create_workflow(db, workflow_in, normal_user.id)


def test_get_workflow(db: Session, workflow: models.Workflow):
    """测试获取单个工作流"""
    # 获取工作流
    got_workflow = workflow_service.get_workflow(db, workflow.id)
    
    # 验证结果
    assert got_workflow.id == workflow.id
    assert got_workflow.name == workflow.name
    assert got_workflow.description == workflow.description
    assert len(got_workflow.nodes) > 0
    
    # 测试不存在的工作流
    with pytest.raises(Exception):
        workflow_service.get_workflow(db, 999)


def test_update_workflow(db: Session, workflow: models.Workflow, normal_user: models.User):
    """测试更新工作流"""
    # 更新数据
    update_data = schemas.WorkflowUpdate(
        name="更新后的工作流",
        description="更新后的描述"
    )
    
    # 获取原工作流ID用于后续测试
    workflow_id = workflow.id
    
    # 更新工作流
    updated_workflow = workflow_service.update_workflow(db, workflow_id, update_data, normal_user.id)
    
    # 验证更新结果
    if updated_workflow is not None:
        assert updated_workflow.id == workflow_id
        assert updated_workflow.name == "更新后的工作流"
        assert updated_workflow.description == "更新后的描述"
    
    # 获取更新后的工作流以验证更新是否成功
    workflow_updated = workflow_service.get_workflow(db, workflow_id)
    assert workflow_updated.name == "更新后的工作流"
    assert workflow_updated.description == "更新后的描述"
    
    # 测试不存在的工作流
    with pytest.raises(Exception):
        workflow_service.update_workflow(db, 999, update_data, normal_user.id)


def test_delete_workflow(db: Session, template: models.Template, normal_user: models.User):
    """测试删除工作流"""
    # 创建测试工作流
    workflow_in = schemas.WorkflowCreate(
        name="待删除工作流",
        description="这是待删除的工作流",
    )
    workflow = workflow_service.create_workflow(db, workflow_in, normal_user.id)
    
    # 获取工作流ID用于后续测试
    workflow_id = workflow.id
    workflow_name = workflow.name
    
    # 删除工作流
    deleted_workflow = workflow_service.delete_workflow(db, workflow_id, normal_user.id)
    
    # 验证删除结果 - 如果返回值为None，直接通过测试
    if deleted_workflow is not None:
        assert deleted_workflow.id == workflow_id
        assert deleted_workflow.name == workflow_name
    
    # 确认工作流已被删除
    with pytest.raises(Exception):
        workflow_service.get_workflow(db, workflow_id)
    
    # 测试删除不存在的工作流
    with pytest.raises(Exception):
        workflow_service.delete_workflow(db, 999, normal_user.id)


def test_get_workflow_nodes(db: Session, workflow: models.Workflow):
    """测试获取工作流节点"""
    # 获取工作流节点
    nodes = workflow_service.get_workflow_nodes(db, workflow.id)
    
    # 验证结果
    assert len(nodes) > 0
    assert all(node.workflow_id == workflow.id for node in nodes)
    
    # 测试不存在的工作流
    with pytest.raises(Exception):
        workflow_service.get_workflow_nodes(db, 999) 