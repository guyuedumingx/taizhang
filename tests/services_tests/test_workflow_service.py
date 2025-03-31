from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.services.workflow.workflow_service import workflow_service

def test_get_workflows(db: Session, workflow: models.Workflow, template: models.Template):
    """测试获取工作流列表"""
    # 再创建一个测试工作流
    workflow_in = schemas.WorkflowCreate(
        name="测试工作流2",
        description="这是测试工作流2",
        nodes=[]
    )
    workflow2 = workflow_service.create_workflow(db, workflow_in, 1)
    
    # 创建关联到workflow2的模板
    template_in = schemas.TemplateCreate(
        name="关联模板",
        description="关联到workflow2的模板",
        department="测试部门",
        workflow_id=workflow2.id,
        fields=[]
    )
    template2 = crud.template.create(db, obj_in=template_in, creator_id=1)

    # 测试获取所有工作流
    workflows = workflow_service.get_workflows(db)
    assert len(workflows) >= 2

    # 测试按模板筛选
    workflows = workflow_service.get_workflows(db, template_id=template2.id)
    assert len(workflows) >= 1
    # 检查筛选出的工作流是否包含正确的ID
    assert any(w.id == workflow2.id for w in workflows)

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
                order_index=1
            )
        ]
    )

    # 创建工作流
    workflow = workflow_service.create_workflow(db, workflow_in, normal_user.id)
    
    # 更新模板，让它关联到新创建的工作流
    template.workflow_id = workflow.id
    db.add(template)
    db.commit()
    db.refresh(template)

    # 验证创建结果
    assert workflow.name == "新工作流"
    assert workflow.description == "这是一个新工作流"
    assert template.workflow_id == workflow.id
    
    # 检查是否创建了节点
    nodes = crud.workflow_node.get_by_workflow(db, workflow_id=workflow.id)
    assert len(nodes) == 1

def test_get_workflow(db: Session, workflow: models.Workflow, template: models.Template):
    """测试获取单个工作流"""
    # 确保模板关联到工作流
    template.workflow_id = workflow.id
    db.add(template)
    db.commit()
    
    # 获取工作流
    got_workflow = workflow_service.get_workflow(db, workflow.id)
    
    # 验证结果
    assert got_workflow.id == workflow.id
    assert got_workflow.name == workflow.name
    assert got_workflow.description == workflow.description
    assert hasattr(got_workflow, 'template_name')  # 应该有关联的模板名称

def test_update_workflow(db: Session, workflow: models.Workflow):
    """测试更新工作流"""
    # 更新数据
    workflow_update = schemas.WorkflowUpdate(
        name="更新后的工作流",
        description="这是更新后的工作流描述"
    )

    # 执行更新
    updated_workflow = workflow_service.update_workflow(db, workflow.id, workflow_update, 1)

    # 验证更新结果
    assert updated_workflow.name == "更新后的工作流"
    assert updated_workflow.description == "这是更新后的工作流描述"

def test_delete_workflow(db: Session):
    """测试删除工作流"""
    # 创建新工作流用于删除测试
    workflow_in = schemas.WorkflowCreate(
        name="待删除工作流",
        description="这个工作流将被删除",
        nodes=[]
    )
    workflow = workflow_service.create_workflow(db, workflow_in, 1)

    # 执行删除
    deleted_workflow = workflow_service.delete_workflow(db, workflow.id, 1)

    # 验证删除结果
    assert deleted_workflow.id == workflow.id
    assert workflow_service.get_workflows(db, search="待删除工作流") == []

def test_get_workflow_nodes(db: Session, workflow: models.Workflow):
    """测试获取工作流节点列表"""
    # 创建节点
    node_in = schemas.WorkflowNodeCreate(
        name="测试节点",
        description="这是一个测试节点",
        node_type="approval",
        order_index=1,
        workflow_id=workflow.id
    )
    node = models.WorkflowNode(**node_in.dict())
    db.add(node)
    db.commit()

    # 获取节点
    nodes = workflow_service.get_workflow_nodes(db, workflow.id)

    # 验证结果
    assert len(nodes) >= 1
    assert any(n.name == "测试节点" for n in nodes) 