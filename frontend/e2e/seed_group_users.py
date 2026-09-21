"""E2E 测试辅助: 造组范围权限测试用户（幂等）"""
import sys
sys.path.insert(0, '.')
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user


def main():
    db = SessionLocal()

    def mk(username, ehr, name, dept, role):
        u = db.query(User).filter(User.ehr_id == ehr).first()
        if u:
            return u
        u = User(username=username, ehr_id=ehr, hashed_password=get_password_hash('test1234'),
                 name=name, department=dept, is_active=True)
        db.add(u)
        db.commit()
        db.refresh(u)
        add_role_for_user(str(u.id), role)
        return u

    mk('leader1', '1000002', '李组长', '测试一组', 'leader')
    mk('other1', '2000001', '王五', '测试二组', 'user')
    mk('leader2', '2000002', '赵组长', '测试二组', 'leader')
    print('group test users ready')
    db.close()


if __name__ == '__main__':
    main()
