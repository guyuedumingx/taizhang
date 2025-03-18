import logging
from sqlalchemy.orm import Session

from app import models, crud, schemas
from app.core.config import settings
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, add_permission_for_role, get_enforcer_instance
import os

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
    """
    初始化数据库
    创建第一个超级用户
    """
    # Casbin 规则表初始化
    init_casbin_rules(db)
    
    # 超级管理员角色
    create_admin_role(db)
    
    # 创建超级用户
    if settings.FIRST_SUPERUSER:
        user = crud.user.get_by_username(db, username=settings.FIRST_SUPERUSER)
        if not user:
            user_in = schemas.UserCreate(
                username=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
                ehr_id="admin",
                name="超级管理员",
                department="系统",
            )
            user = crud.user.create(db, obj_in=user_in)
            logger.info(f"已创建超级用户: {settings.FIRST_SUPERUSER}")
            
            # 添加超级管理员角色
            admin_role = crud.role.get_by_name(db, name="admin")
            if admin_role:
                # 为超级用户添加超级管理员角色
                e = get_enforcer_instance()
                e.add_grouping_policy(str(user.id), "admin")
                logger.info(f"已为超级用户 {user.username} 分配超级管理员角色")
        else:
            logger.info(f"超级用户已存在: {settings.FIRST_SUPERUSER}")
    else:
        logger.warning("未设置超级用户，跳过初始化超级用户")

def create_admin_role(db: Session) -> None:
    """创建超级管理员角色"""
    # 检查是否已存在
    admin_role = crud.role.get_by_name(db, name="admin")
    if not admin_role:
        # 创建超级管理员角色
        role_in = schemas.RoleCreate(
            name="admin",
            description="超级管理员",
        )
        admin_role = crud.role.create(db, obj_in=role_in)
        logger.info("已创建超级管理员角色")
        
        # 将所有系统权限添加到超级管理员角色
        e = get_enforcer_instance()
        e.add_policy("admin", "*", "*")
        logger.info("已为超级管理员角色添加所有权限")
    else:
        logger.info("超级管理员角色已存在")

def init_casbin_rules(db: Session) -> None:
    """初始化 Casbin 规则表"""
    # 获取 enforcer 实例来触发表创建
    e = get_enforcer_instance()
    logger.info("已初始化 Casbin 规则表") 