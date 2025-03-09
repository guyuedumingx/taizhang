import casbin
import os
from app.core.config import settings

# 创建Casbin执行器，使用文件适配器代替SQLAlchemy适配器
# 使用绝对路径
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
model_path = os.path.join(base_dir, settings.CASBIN_MODEL_PATH)
policy_path = os.path.join(os.path.dirname(model_path), "policy.csv")

# 确保策略文件存在
if not os.path.exists(policy_path):
    with open(policy_path, "w") as f:
        f.write("")  # 创建空文件

# 创建Casbin执行器
enforcer = casbin.Enforcer(model_path, policy_path)

# 添加角色和权限
def add_permission_for_role(role: str, resource: str, action: str) -> bool:
    """
    为角色添加权限
    """
    result = enforcer.add_policy(role, resource, action)
    enforcer.save_policy()
    return result

# 删除角色的权限
def remove_permission_for_role(role: str, resource: str, action: str) -> bool:
    """
    删除角色的权限
    """
    result = enforcer.remove_policy(role, resource, action)
    enforcer.save_policy()
    return result

# 为用户分配角色
def add_role_for_user(user_id: str, role: str) -> bool:
    """
    为用户分配角色
    """
    result = enforcer.add_grouping_policy(user_id, role)
    enforcer.save_policy()
    return result

# 删除用户的角色
def remove_role_for_user(user_id: str, role: str) -> bool:
    """
    删除用户的角色
    """
    result = enforcer.remove_grouping_policy(user_id, role)
    enforcer.save_policy()
    return result

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