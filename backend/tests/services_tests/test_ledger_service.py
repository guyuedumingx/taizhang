import pytest
from sqlalchemy.orm import Session
from io import BytesIO

from app import models, schemas
from app.services.ledger_service import ledger_service


def test_get_ledgers(db: Session, ledger: models.Ledger, normal_user: models.User, template: models.Template, team: models.Team):
    """测试获取台账列表"""
    # 再创建一个测试台账
    ledger_in = schemas.LedgerCreate(
        name="测试台账2",
        description="这是测试台账2",
        team_id=team.id,
        template_id=template.id,
        data={"字段1": "值1", "字段2": 200}
    )
    crud_ledger = models.Ledger(
        name=ledger_in.name,
        description=ledger_in.description,
        team_id=ledger_in.team_id,
        template_id=ledger_in.template_id,
        data=ledger_in.data,
        status="draft",
        approval_status="pending",
        created_by_id=normal_user.id,
        updated_by_id=normal_user.id
    )
    db.add(crud_ledger)
    db.commit()
    db.refresh(crud_ledger)
    
    # 测试获取所有台账
    ledgers = ledger_service.get_ledgers(db, current_user=normal_user)
    assert len(ledgers) == 2
    
    # 测试按团队筛选
    ledgers = ledger_service.get_ledgers(db, team_id=team.id, current_user=normal_user)
    assert len(ledgers) == 2
    assert ledgers[0].team_id == team.id
    
    # 测试按模板筛选
    ledgers = ledger_service.get_ledgers(db, template_id=template.id, current_user=normal_user)
    assert len(ledgers) == 2
    assert ledgers[0].template_id == template.id
    
    # 测试按状态筛选
    ledgers = ledger_service.get_ledgers(db, status="draft", current_user=normal_user)
    assert len(ledgers) == 2
    assert ledgers[0].status == "draft"
    
    # 测试按名称搜索
    ledgers = ledger_service.get_ledgers(db, search="台账2", current_user=normal_user)
    assert len(ledgers) == 1
    assert "台账2" in ledgers[0].name
    
    # 测试分页
    ledgers = ledger_service.get_ledgers(db, skip=1, limit=1, current_user=normal_user)
    assert len(ledgers) == 1


def test_create_ledger(db: Session, normal_user: models.User, template: models.Template, team: models.Team):
    """测试创建台账"""
    # 测试数据
    ledger_in = schemas.LedgerCreate(
        name="新台账",
        description="这是一个新台账",
        team_id=team.id,
        template_id=template.id,
        data={"字段1": "测试值", "字段2": 300}
    )
    
    # 创建台账
    ledger = ledger_service.create_ledger(db, ledger_in, normal_user)
    
    # 验证创建结果
    assert ledger.name == "新台账"
    assert ledger.description == "这是一个新台账"
    assert ledger.team_id == team.id
    assert ledger.template_id == template.id
    assert ledger.data["字段1"] == "测试值"
    assert ledger.data["字段2"] == 300
    assert ledger.status == "draft"
    assert ledger.approval_status == "draft"
    assert ledger.created_by_id == normal_user.id
    assert ledger.updated_by_id == normal_user.id
    
    # 测试创建台账时模板不存在
    invalid_ledger_in = schemas.LedgerCreate(
        name="无效台账",
        description="这是一个无效台账",
        team_id=team.id,
        template_id=999,  # 不存在的模板ID
        data={}
    )
    with pytest.raises(Exception):
        ledger_service.create_ledger(db, invalid_ledger_in, normal_user)


def test_get_ledger(db: Session, ledger: models.Ledger, normal_user: models.User):
    """测试获取单个台账"""
    # 获取台账
    got_ledger = ledger_service.get_ledger(db, ledger.id, normal_user)
    
    # 验证结果
    assert got_ledger.id == ledger.id
    assert got_ledger.name == ledger.name
    assert got_ledger.description == ledger.description
    assert got_ledger.team_id == ledger.team_id
    assert got_ledger.template_id == ledger.template_id
    
    # 测试不存在的台账
    with pytest.raises(Exception):
        ledger_service.get_ledger(db, 999, normal_user)


def test_update_ledger(db: Session, ledger: models.Ledger, normal_user: models.User):
    """测试更新台账"""
    # 更新数据
    update_data = schemas.LedgerUpdate(
        name="更新后的台账",
        description="更新后的描述",
        data={"字段1": "更新后的值", "字段2": 500}
    )
    
    # 更新台账
    updated_ledger = ledger_service.update_ledger(db, ledger.id, update_data, normal_user)
    
    # 验证更新结果
    assert updated_ledger.name == "更新后的台账"
    assert updated_ledger.description == "更新后的描述"
    assert updated_ledger.data["字段1"] == "更新后的值"
    assert updated_ledger.data["字段2"] == 500
    assert updated_ledger.updated_by_id == normal_user.id
    
    # 测试不存在的台账
    with pytest.raises(Exception):
        ledger_service.update_ledger(db, 999, update_data, normal_user)


def test_delete_ledger(db: Session, normal_user: models.User, template: models.Template, team: models.Team):
    """测试删除台账"""
    # 创建测试数据
    ledger_in = schemas.LedgerCreate(
        name="待删除台账",
        description="这是待删除的台账",
        team_id=team.id,
        template_id=template.id,
        data={}
    )
    ledger = ledger_service.create_ledger(db, ledger_in, normal_user)
    
    # 删除台账
    deleted_ledger = ledger_service.delete_ledger(db, ledger.id, normal_user)
    
    # 验证删除结果
    assert deleted_ledger.id == ledger.id
    assert deleted_ledger.name == "待删除台账"
    
    # 确认台账已被删除
    with pytest.raises(Exception):
        ledger_service.get_ledger(db, ledger.id, normal_user)
    
    # 测试删除不存在的台账
    with pytest.raises(Exception):
        ledger_service.delete_ledger(db, 999, normal_user)


def test_export_ledger(db: Session, ledger: models.Ledger, normal_user: models.User):
    """测试导出台账"""
    # 测试Excel导出
    file_data, filename, content_type = ledger_service.export_ledger(db, ledger.id, "excel", normal_user)
    
    # 验证导出结果
    assert isinstance(file_data, BytesIO)
    assert "xlsx" in filename
    assert "spreadsheet" in content_type
    
    # 测试CSV导出
    file_data, filename, content_type = ledger_service.export_ledger(db, ledger.id, "csv", normal_user)
    
    # 验证导出结果
    assert isinstance(file_data, BytesIO)
    assert "csv" in filename
    assert "csv" in content_type
    
    # 测试TXT导出
    file_data, filename, content_type = ledger_service.export_ledger(db, ledger.id, "txt", normal_user)
    
    # 验证导出结果
    assert isinstance(file_data, BytesIO)
    assert "txt" in filename
    assert "plain" in content_type
    
    # 测试不存在的台账
    with pytest.raises(Exception):
        ledger_service.export_ledger(db, 999, "excel", normal_user)


def test_export_all_ledgers(db: Session, ledger: models.Ledger, normal_user: models.User, template: models.Template):
    """测试导出所有台账"""
    # 测试Excel导出
    file_data, filename, content_type = ledger_service.export_all_ledgers(db, "excel", current_user=normal_user)
    
    # 验证导出结果
    assert isinstance(file_data, BytesIO)
    assert "xlsx" in filename
    assert "spreadsheet" in content_type
    
    # 测试按模板筛选导出
    file_data, filename, content_type = ledger_service.export_all_ledgers(db, "excel", template_id=template.id, current_user=normal_user)
    
    # 验证导出结果
    assert isinstance(file_data, BytesIO)
    assert "xlsx" in filename
    assert template.name in filename or str(template.id) in filename 