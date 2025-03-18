from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import User
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user

def create_test_user():
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        user = db.query(User).filter(User.username == "testuser").first()
        if user:
            print(f"测试用户已存在: username={user.username}, ehr_id={user.ehr_id}")
            return user
        
        # 创建测试用户
        user = User(
            username="testuser",
            ehr_id="1234567",
            hashed_password=get_password_hash("password123"),
            name="测试用户",
            department="测试部门",
            is_active=True,
            is_superuser=True,  # 设为超级管理员方便测试
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 为用户分配角色
        add_role_for_user(str(user.id), "admin")
        
        print(f"已创建测试用户: username={user.username}, ehr_id={user.ehr_id}")
        return user
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user() 