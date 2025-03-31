from app import crud, models, schemas
from sqlalchemy.orm import Session
from .utils import random_lower_string, random_email


def create_random_user(db: Session, email=None, password=None):
    """
    创建随机测试用户
    """
    if email is None:
        email = random_email()
    if password is None:
        password = random_lower_string()
    
    # 生成随机用户名和EHR ID
    username = random_lower_string(8)
    # EHR ID需要7位数字
    ehr_id = f"{100_0000 + abs(hash(username)) % 900_0000}"[-7:]  # 确保是7位数字
    name = f"测试用户_{username[:5]}"
    
    user_in = schemas.UserCreate(
        username=username,
        ehr_id=ehr_id,
        password=password,
        name=name,
        email=email,  # 可能不是必需的，但测试代码在使用
        is_active=True,
        is_superuser=False,
        department="测试部门",
    )
    
    user = crud.user.create(db, obj_in=user_in)
    return user 