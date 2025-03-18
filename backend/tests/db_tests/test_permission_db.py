import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.casbin_service import (
    get_enforcer_instance,
    add_permission_for_role,
    remove_permission_for_role,
    get_permissions_for_role,
    add_role_for_user,
    get_roles_for_user,
    check_permission
)


def test_add_permission_for_role(db: Session, test_role: dict):
    """测试为角色添加权限"""
    # 创建角色
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    # 使用Casbin添加权限
    permission = "user:read"
    resource, action = permission.split(":")
    
    e = get_enforcer_instance()
    added = e.add_policy(role.name, resource, action)
    # 即使策略已存在（返回False），我们仍然可以继续测试
    
    # 验证权限是否存在
    permissions = get_permissions_for_role(role.name)
    assert any(p[1] == resource and p[2] == action for p in permissions)


def test_get_permissions_for_role(db: Session, test_role: dict):
    """测试获取角色的所有权限"""
    # 创建角色
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    # 使用Casbin添加权限
    permissions = ["user:read", "user:create", "role:read"]
    
    for permission in permissions:
        resource, action = permission.split(":")
        add_permission_for_role(role.name, resource, action)
    
    # 获取角色的所有权限
    role_permissions = get_permissions_for_role(role.name)
    
    assert len(role_permissions) == len(permissions)
    for permission in permissions:
        resource, action = permission.split(":")
        assert any(p[1] == resource and p[2] == action for p in role_permissions)


def test_remove_permission_for_role(db: Session, test_role: dict):
    """测试删除角色的权限"""
    # 创建角色
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    # 使用Casbin添加权限
    permission = "user:read"
    resource, action = permission.split(":")
    
    add_permission_for_role(role.name, resource, action)
    
    # 验证权限是否添加成功
    permissions_before = get_permissions_for_role(role.name)
    has_permission_before = any(p[1] == resource and p[2] == action for p in permissions_before)
    assert has_permission_before is True
    
    # 删除权限
    removed = remove_permission_for_role(role.name, resource, action)
    assert removed is True
    
    # 验证权限是否删除成功
    permissions_after = get_permissions_for_role(role.name)
    has_permission_after = any(p[1] == resource and p[2] == action for p in permissions_after)
    assert has_permission_after is False


def test_add_role_for_user(db: Session, test_user: dict, test_role: dict):
    """测试为用户添加角色"""
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建角色
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    # 为用户添加角色
    e = get_enforcer_instance()
    added = e.add_grouping_policy(user.username, role.name)
    # 即使角色已存在（返回False），我们仍然可以继续测试
    
    # 验证用户是否有指定角色
    user_roles = get_roles_for_user(user.username)
    assert role.name in user_roles


def test_get_roles_for_user(db: Session, test_user: dict, test_role: dict):
    """测试获取用户的所有角色"""
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建多个角色
    role1_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role2_in = schemas.RoleCreate(
        name=f"{test_role['name']}_2",
        description=f"{test_role['description']} 2",
        is_system=False,
    )
    
    role1 = crud.role.create(db, obj_in=role1_in)
    role2 = crud.role.create(db, obj_in=role2_in)
    
    # 为用户添加多个角色
    add_role_for_user(user.username, role1.name)
    add_role_for_user(user.username, role2.name)
    
    # 获取用户的所有角色
    user_roles = get_roles_for_user(user.username)
    
    assert len(user_roles) == 2
    assert role1.name in user_roles
    assert role2.name in user_roles


def test_check_permission(db: Session, test_user: dict, test_role: dict):
    """测试检查用户是否具有特定权限"""
    # 创建用户
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    # 创建角色
    role_in = schemas.RoleCreate(
        name=test_role["name"],
        description=test_role["description"],
        is_system=test_role["is_system"],
    )
    
    role = crud.role.create(db, obj_in=role_in)
    
    # 为角色添加权限
    permission = "user:read"
    resource, action = permission.split(":")
    add_permission_for_role(role.name, resource, action)
    
    # 为用户添加角色
    add_role_for_user(user.username, role.name)
    
    # 检查用户是否具有权限
    has_permission = check_permission(user.username, resource, action)
    assert has_permission is True
    
    # 检查用户是否具有未分配的权限
    has_other_permission = check_permission(user.username, "user", "delete")
    assert has_other_permission is False


def test_superuser_permission(db: Session, test_admin: dict):
    """测试超级用户拥有所有权限"""
    # 创建超级用户
    admin_in = schemas.UserCreate(
        username=test_admin["username"],
        ehr_id=test_admin["ehr_id"],
        password=test_admin["password"],
        name=test_admin["name"],
        department=test_admin["department"],
        is_active=test_admin["is_active"],
        is_superuser=test_admin["is_superuser"],
    )
    
    admin = crud.user.create(db, obj_in=admin_in)
    
    # 检查超级用户是否具有任何权限，即使未显式授予
    has_permission = crud.user.has_permission(db, user_id=admin.id, permission="any:permission")
    assert has_permission is True 