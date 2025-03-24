import os
import casbin
from app.core.config import settings

def get_enforcer():
    """获取Casbin enforcer实例"""
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "rbac_model.conf")
    
    # 使用SQLite适配器
    from casbin_sqlalchemy_adapter import Adapter
    from sqlalchemy import create_engine
    
    # 获取数据库URL
    database_url = settings.SQLALCHEMY_DATABASE_URI
    
    # 创建SQLAlchemy适配器
    adapter = Adapter(create_engine(database_url))
    
    # 创建并返回enforcer
    return casbin.Enforcer(model_path, adapter)

# 获取enforcer单例
_enforcer = None

def get_enforcer_instance():
    """获取enforcer单例"""
    global _enforcer
    if _enforcer is None:
        _enforcer = get_enforcer()
    return _enforcer

def add_permission_for_role(role: str, resource: str, action: str) -> bool:
    """为角色添加权限"""
    e = get_enforcer_instance()
    return e.add_policy(role, resource, action)

def remove_permission_for_role(role: str, resource: str, action: str) -> bool:
    """移除角色的权限"""
    e = get_enforcer_instance()
    return e.remove_policy(role, resource, action)

def add_role_for_user(user_id: str, role: str) -> bool:
    """为用户添加角色"""
    e = get_enforcer_instance()
    return e.add_grouping_policy(str(user_id), role)

def remove_role_for_user(user_id: str, role: str) -> bool:
    """移除用户的角色"""
    e = get_enforcer_instance()
    return e.remove_grouping_policy(str(user_id), role)

def get_roles_for_user(user_id: str) -> list:
    """获取用户的所有角色"""
    try:
        e = get_enforcer_instance()
        if e is None:
            print("Enforcer实例为空")
            return ["user"]  # 默认返回user角色
        roles = e.get_roles_for_user(str(user_id))
        if not roles:
            return ["user"]  # 如果没有找到角色，返回默认user角色
        return roles
    except Exception as e:
        print(f"获取用户角色时出错: {str(e)}")
        return ["user"]  # 出错时返回默认user角色

def get_permissions_for_role(role: str) -> list:
    """获取角色的所有权限"""
    e = get_enforcer_instance()
    return e.get_permissions_for_user(role)

def check_permission(user_id: str, resource: str, action: str) -> bool:
    """检查用户是否有特定权限"""
    e = get_enforcer_instance()
    return e.enforce(str(user_id), resource, action) 