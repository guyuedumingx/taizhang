import logging
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, add_permission_for_role

logger = logging.getLogger(__name__)


# 初始化权限
def init_permissions():
    # 定义权限
    permissions = {
        "admin": [
            # 管理员拥有所有权限
            ("ledger", "view"),
            ("ledger", "create"),
            ("ledger", "edit"),
            ("ledger", "delete"),
            ("ledger", "export"),
            ("template", "view"),
            ("template", "create"),
            ("template", "edit"),
            ("template", "delete"),
            ("user", "view"),
            ("user", "create"),
            ("user", "edit"),
            ("user", "delete"),
            ("role", "view"),
            ("role", "create"),
            ("role", "edit"),
            ("role", "delete"),
            ("team", "view"),
            ("team", "create"),
            ("team", "edit"),
            ("team", "delete"),
        ],
        "manager": [
            # 经理权限
            ("ledger", "view"),
            ("ledger", "create"),
            ("ledger", "edit"),
            ("ledger", "delete"),
            ("ledger", "export"),
            ("template", "view"),
            ("template", "create"),
            ("template", "edit"),
            ("user", "view"),
        ],
        "user": [
            # 普通用户权限
            ("ledger", "view"),
            ("ledger", "create"),
            ("ledger", "edit"),
            ("ledger", "export"),
            ("template", "view"),
        ],
    }
    
    # 添加权限
    for role, perms in permissions.items():
        for resource, action in perms:
            add_permission_for_role(role, resource, action)
            logger.info(f"Added permission: {role} - {resource}:{action}")


# 初始化角色
def init_roles(db: Session):
    roles = [
        {"name": "admin", "description": "系统管理员", "is_system": True},
        {"name": "manager", "description": "部门经理", "is_system": True},
        {"name": "user", "description": "普通用户", "is_system": True},
    ]
    
    for role_data in roles:
        role = db.query(models.Role).filter(models.Role.name == role_data["name"]).first()
        if not role:
            role = models.Role(**role_data)
            db.add(role)
            db.commit()
            logger.info(f"Created role: {role.name}")


# 初始化管理员用户
def init_admin_user(db: Session):
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin_user = models.User(
            username="admin",
            ehr_id="0000001",
            hashed_password=get_password_hash("admin123"),
            name="系统管理员",
            department="系统",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # 为管理员分配角色
        add_role_for_user(str(admin_user.id), "admin")
        logger.info(f"Created admin user: {admin_user.username}")


# 初始化数据库
def init_db(db: Session) -> None:
    # 初始化角色
    init_roles(db)
    
    # 初始化权限
    init_permissions()
    
    # 初始化管理员用户
    init_admin_user(db) 