import casbin
import casbin_sqlalchemy_adapter
from sqlalchemy import create_engine

from app.core.config import settings

# 创建Casbin适配器
adapter = casbin_sqlalchemy_adapter.Adapter(settings.SQLALCHEMY_DATABASE_URI)

# 创建Casbin执行器
enforcer = casbin.Enforcer(settings.CASBIN_MODEL_PATH, adapter)

# 添加角色和权限
def add_permission_for_role(role: str, resource: str, action: str) -> bool:
    """
    为角色添加权限
    """
    return enforcer.add_policy(role, resource, action)

# 删除角色的权限
def remove_permission_for_role(role: str, resource: str, action: str) -> bool:
    """
    删除角色的权限
    """
    return enforcer.remove_policy(role, resource, action)

# 为用户分配角色
def add_role_for_user(user_id: str, role: str) -> bool:
    """
    为用户分配角色
    """
    return enforcer.add_grouping_policy(user_id, role)

# 删除用户的角色
def remove_role_for_user(user_id: str, role: str) -> bool:
    """
    删除用户的角色
    """
    return enforcer.remove_grouping_policy(user_id, role)

# 获取用户的所有角色
def get_roles_for_user(user_id: str) -> list:
    """
    获取用户的所有角色
    """
    return enforcer.get_roles_for_user(user_id)

# 获取角色的所有权限
def get_permissions_for_role(role: str) -> list:
    """
    获取角色的所有权限
    """
    return enforcer.get_permissions_for_user(role)

# 检查用户是否有权限
def check_permission(user_id: str, resource: str, action: str) -> bool:
    """
    检查用户是否有权限
    """
    return enforcer.enforce(user_id, resource, action) 