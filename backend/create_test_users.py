from app.db.session import SessionLocal
from app.models.user import User
from app.models.team import Team
from app.models.role import Role
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    db = SessionLocal()
    try:
        # 检查是否已有用户
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info(f"数据库中已有 {user_count} 个用户，跳过创建测试用户")
            return
        
        # 创建团队
        team1 = Team(name="技术部", department="IT", description="负责系统开发和维护")
        team2 = Team(name="财务部", department="Finance", description="负责财务管理")
        db.add(team1)
        db.add(team2)
        db.commit()
        
        # 创建角色
        admin_role = Role(name="admin", description="系统管理员")
        manager_role = Role(name="manager", description="部门经理")
        user_role = Role(name="user", description="普通用户")
        db.add(admin_role)
        db.add(manager_role)
        db.add(user_role)
        db.commit()
        
        # 创建用户
        
        # 1. 管理员用户 - 密码正常
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            name="系统管理员",
            department="IT部门",
            is_active=True,
            is_superuser=True,
            team_id=team1.id,
            last_password_change=datetime.now()
        )
        
        # 2. 经理用户 - 密码过期
        manager = User(
            username="manager",
            email="manager@example.com",
            hashed_password=get_password_hash("manager123"),
            name="部门经理",
            department="财务部",
            is_active=True,
            is_superuser=False,
            team_id=team2.id,
            last_password_change=datetime.now() - timedelta(days=100)  # 密码已过期
        )
        
        # 3. 普通用户 - 密码正常
        user = User(
            username="user",
            email="user@example.com",
            hashed_password=get_password_hash("user123"),
            name="普通用户",
            department="技术部",
            is_active=True,
            is_superuser=False,
            team_id=team1.id,
            last_password_change=datetime.now()
        )
        
        # 4. 即将过期用户 - 密码即将过期
        expiring_user = User(
            username="expiring",
            email="expiring@example.com",
            hashed_password=get_password_hash("expiring123"),
            name="即将过期用户",
            department="技术部",
            is_active=True,
            is_superuser=False,
            team_id=team1.id,
            last_password_change=datetime.now() - timedelta(days=85)  # 密码即将过期
        )
        
        db.add(admin)
        db.add(manager)
        db.add(user)
        db.add(expiring_user)
        db.commit()
        
        # 分配角色
        add_role_for_user(str(admin.id), "admin")
        add_role_for_user(str(manager.id), "manager")
        add_role_for_user(str(user.id), "user")
        add_role_for_user(str(expiring_user.id), "user")
        
        logger.info("测试用户创建成功")
        logger.info("管理员: admin/admin123")
        logger.info("经理(密码已过期): manager/manager123")
        logger.info("普通用户: user/user123")
        logger.info("即将过期用户: expiring/expiring123")
        
    except Exception as e:
        logger.error(f"创建测试用户失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users() 