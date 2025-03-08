from app.db.session import SessionLocal
from app.models.user import User
from app.models.team import Team
from app.models.role import Role
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_users():
    db = SessionLocal()
    try:
        # 删除所有用户
        user_count = db.query(User).count()
        db.query(User).delete()
        
        # 删除所有团队
        team_count = db.query(Team).count()
        db.query(Team).delete()
        
        # 删除所有角色
        role_count = db.query(Role).count()
        db.query(Role).delete()
        
        db.commit()
        
        logger.info(f"已删除 {user_count} 个用户, {team_count} 个团队, {role_count} 个角色")
        
    except Exception as e:
        logger.error(f"清空用户表失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_users() 