import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.security import verify_password


def test_create_user(db: Session, test_user: dict):
    """测试创建用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    user = crud.user.create(db, obj_in=user_in)
    
    assert user.username == test_user["username"]
    assert user.ehr_id == test_user["ehr_id"]
    assert user.name == test_user["name"]
    assert user.department == test_user["department"]
    assert user.is_active == test_user["is_active"]
    assert user.is_superuser == test_user["is_superuser"]
    assert verify_password(test_user["password"], user.hashed_password)


def test_get_user(db: Session, test_user: dict):
    """测试获取用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    created_user = crud.user.create(db, obj_in=user_in)
    
    fetched_user = crud.user.get(db, id=created_user.id)
    
    assert fetched_user
    assert fetched_user.id == created_user.id
    assert fetched_user.username == test_user["username"]
    assert fetched_user.ehr_id == test_user["ehr_id"]


def test_get_user_by_ehr_id(db: Session, test_user: dict):
    """测试通过EHR ID获取用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    crud.user.create(db, obj_in=user_in)
    
    fetched_user = crud.user.get_by_ehr_id(db, ehr_id=test_user["ehr_id"])
    
    assert fetched_user
    assert fetched_user.username == test_user["username"]
    assert fetched_user.ehr_id == test_user["ehr_id"]


def test_get_user_by_username(db: Session, test_user: dict):
    """测试通过用户名获取用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    crud.user.create(db, obj_in=user_in)
    
    fetched_user = crud.user.get_by_username(db, username=test_user["username"])
    
    assert fetched_user
    assert fetched_user.username == test_user["username"]
    assert fetched_user.ehr_id == test_user["ehr_id"]


def test_update_user(db: Session, test_user: dict):
    """测试更新用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    created_user = crud.user.create(db, obj_in=user_in)
    
    new_name = "Updated Name"
    new_department = "Updated Department"
    
    user_update = schemas.UserUpdate(
        name=new_name,
        department=new_department,
    )
    
    updated_user = crud.user.update(db, db_obj=created_user, obj_in=user_update)
    
    assert updated_user.id == created_user.id
    assert updated_user.name == new_name
    assert updated_user.department == new_department
    assert updated_user.username == test_user["username"]  # 没有更新的字段应保持不变


def test_delete_user(db: Session, test_user: dict):
    """测试删除用户"""
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    created_user = crud.user.create(db, obj_in=user_in)
    user_id = created_user.id
    
    deleted_user = crud.user.remove(db, id=user_id)
    
    assert deleted_user.id == user_id
    
    # 确认用户已被删除
    fetched_user = crud.user.get(db, id=user_id)
    assert fetched_user is None


def test_get_multi_users(db: Session, test_user: dict, test_admin: dict):
    """测试获取多个用户"""
    # 创建第一个用户
    user1_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
    )
    
    # 创建第二个用户
    user2_in = schemas.UserCreate(
        username=test_admin["username"],
        ehr_id=test_admin["ehr_id"],
        password=test_admin["password"],
        name=test_admin["name"],
        department=test_admin["department"],
        is_active=test_admin["is_active"],
        is_superuser=test_admin["is_superuser"],
    )
    
    crud.user.create(db, obj_in=user1_in)
    crud.user.create(db, obj_in=user2_in)
    
    users = crud.user.get_multi(db)
    
    assert len(users) == 2
    assert any(u.username == test_user["username"] for u in users)
    assert any(u.username == test_admin["username"] for u in users)


def test_get_multi_by_team(db: Session, test_user: dict, test_team: dict):
    """测试获取团队中的所有用户"""
    # 创建团队
    team_in = schemas.TeamCreate(
        name=test_team["name"],
        department=test_team["department"],
        description=test_team["description"],
    )
    
    team = crud.team.create(db, obj_in=team_in)
    
    # 创建用户并分配到团队
    user_in = schemas.UserCreate(
        username=test_user["username"],
        ehr_id=test_user["ehr_id"],
        password=test_user["password"],
        name=test_user["name"],
        department=test_user["department"],
        is_active=test_user["is_active"],
        is_superuser=test_user["is_superuser"],
        team_id=team.id,
    )
    
    crud.user.create(db, obj_in=user_in)
    
    # 创建不在该团队的用户
    another_user_in = schemas.UserCreate(
        username="another_user",
        ehr_id="9876543",  # 改为7位
        password="password123",
        name="Another User",
        department="Another Department",
        is_active=True,
        is_superuser=False,
    )
    
    crud.user.create(db, obj_in=another_user_in)
    
    # 获取团队中的用户
    team_users = crud.user.get_multi_by_team(db, team_id=team.id)
    
    assert len(team_users) == 1
    assert team_users[0].username == test_user["username"]
    assert team_users[0].team_id == team.id 