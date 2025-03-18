import pytest
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.role.role_service import RoleService


def test_get_roles(db: Session, role: models.Role):
    """测试获取角色列表"""
    # 再创建一个测试角色
    role_in = schemas.RoleCreate(
        name="测试角色2",
        description="这是测试角色2",
        permissions=["user:read", "ledger:read"]
    )
    role2 = models.Role(
        name=role_in.name,
        description=role_in.description,
        is_system=False
    )
    db.add(role2)
    db.commit()
    db.refresh(role2)
    
    # 测试获取所有角色
    roles = RoleService.get_roles(db)
    assert len(roles) >= 2
    
    # 检查角色权限是否正确加载
    for r in roles:
        if r.id == role.id:
            assert "user:create" in r.permissions
            assert "user:read" in r.permissions


def test_create_role(db: Session):
    """测试创建角色"""
    # 创建测试数据
    role_in = schemas.RoleCreate(
        name="新角色",
        description="这是一个新角色",
        permissions=["user:create", "user:update", "user:delete"]
    )
    
    # 创建角色
    role = RoleService.create_role(db, role_in)
    
    # 验证创建结果
    assert role.name == "新角色"
    assert role.description == "这是一个新角色"
    assert "user:create" in role.permissions
    assert "user:update" in role.permissions
    assert "user:delete" in role.permissions
    
    # 测试创建重复名称的角色
    with pytest.raises(Exception):
        RoleService.create_role(db, role_in)


def test_get_role(db: Session, role: models.Role):
    """测试获取单个角色"""
    # 获取角色
    got_role = RoleService.get_role(db, role.id)
    
    # 验证结果
    assert got_role.id == role.id
    assert got_role.name == role.name
    assert got_role.description == role.description
    assert "user:create" in got_role.permissions
    assert "user:read" in got_role.permissions
    
    # 测试不存在的角色
    with pytest.raises(Exception):
        RoleService.get_role(db, 999)


def test_update_role(db: Session, role: models.Role):
    """测试更新角色"""
    # 创建一个非系统角色用于测试
    role_in = schemas.RoleCreate(
        name="可更新角色",
        description="这是可以更新的角色",
        permissions=["user:read"]
    )
    test_role = RoleService.create_role(db, role_in)
    
    # 更新数据
    update_data = schemas.RoleUpdate(
        name="更新后的角色",
        description="更新后的描述",
        permissions=["user:read", "user:update"]
    )
    
    # 更新角色
    updated_role = RoleService.update_role(db, test_role.id, update_data)
    
    # 验证更新结果
    assert updated_role.id == test_role.id
    assert updated_role.name == "更新后的角色"
    assert updated_role.description == "更新后的描述"
    assert "user:read" in updated_role.permissions
    assert "user:update" in updated_role.permissions
    
    # 测试不存在的角色
    with pytest.raises(Exception):
        RoleService.update_role(db, 999, update_data)


def test_delete_role(db: Session):
    """测试删除角色"""
    # 创建测试角色
    role_in = schemas.RoleCreate(
        name="待删除角色",
        description="这是待删除的角色",
        permissions=["user:read"]
    )
    role = RoleService.create_role(db, role_in)
    
    # 删除角色
    deleted_role = RoleService.delete_role(db, role.id)
    
    # 验证删除结果
    assert deleted_role.id == role.id
    assert deleted_role.name == "待删除角色"
    
    # 确认角色已被删除
    with pytest.raises(Exception):
        RoleService.get_role(db, role.id)
    
    # 测试删除不存在的角色
    with pytest.raises(Exception):
        RoleService.delete_role(db, 999)


def test_get_user_roles(db: Session, normal_user: models.User):
    """测试获取用户角色"""
    # 先确保用户有角色
    from app.services.casbin_service import add_role_for_user
    add_role_for_user(str(normal_user.id), "user")
    
    # 获取用户角色
    roles = RoleService.get_user_roles(db, normal_user.id)
    
    # 验证结果
    assert "user" in roles
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        RoleService.get_user_roles(db, 999)


def test_add_user_role(db: Session, normal_user: models.User, role: models.Role):
    """测试添加用户角色"""
    # 添加角色给用户
    result = RoleService.add_user_role(db, normal_user.id, role.name)
    
    # 验证结果
    assert "message" in result
    assert result["message"] == "角色添加成功" or result["message"] == "用户已拥有该角色"
    
    # 检查用户是否真的拥有了这个角色
    roles = RoleService.get_user_roles(db, normal_user.id)
    assert role.name in roles
    
    # 测试添加不存在的角色
    with pytest.raises(Exception):
        RoleService.add_user_role(db, normal_user.id, "nonexistentrole")
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        RoleService.add_user_role(db, 999, role.name)


def test_remove_user_role(db: Session, normal_user: models.User, role: models.Role):
    """测试移除用户角色"""
    # 先确保用户有这个角色
    RoleService.add_user_role(db, normal_user.id, role.name)
    
    # 移除用户角色
    result = RoleService.remove_user_role(db, normal_user.id, role.name)
    
    # 验证结果
    assert "message" in result
    assert result["message"] == "角色删除成功" or result["message"] == "用户没有该角色"
    
    # 检查用户是否真的失去了这个角色
    roles = RoleService.get_user_roles(db, normal_user.id)
    assert role.name not in roles
    
    # 测试移除不存在的角色
    with pytest.raises(Exception):
        RoleService.remove_user_role(db, normal_user.id, "nonexistentrole")
    
    # 测试不存在的用户
    with pytest.raises(Exception):
        RoleService.remove_user_role(db, 999, role.name) 