from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io
from datetime import datetime

from app import models, schemas
from app.api import deps
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, remove_role_for_user, get_roles_for_user, get_permissions_for_role

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户列表
    """
    # 检查权限
    if not deps.check_permissions("user", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    # 获取每个用户的角色
    for user in users:
        user.roles = get_roles_for_user(str(user.id))
    
    return users


@router.post("/", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新用户
    """
    # 检查权限
    if not deps.check_permissions("user", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查用户名是否已存在
    user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="用户名已存在",
        )
    
    # 检查EHR号是否已存在
    user = db.query(models.User).filter(models.User.ehr_id == user_in.ehr_id).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="EHR号已存在",
        )
    
    # 创建用户
    user = models.User(
        username=user_in.username,
        ehr_id=user_in.ehr_id,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        department=user_in.department,
        is_active=True,
        is_superuser=False,
        team_id=user_in.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 为用户分配角色
    if user_in.role:
        add_role_for_user(str(user.id), user_in.role)
    else:
        # 默认角色为普通用户
        add_role_for_user(str(user.id), "user")
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户详情
    """
    # 检查权限
    if not deps.check_permissions("user", "view", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新用户信息
    """
    # 检查权限
    if not deps.check_permissions("user", "edit", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新用户信息
    update_data = user_in.dict(exclude_unset=True)
    
    # 如果更新密码，需要哈希处理
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    
    # 更新角色
    if "role" in update_data:
        role = update_data.pop("role")
        # 获取当前角色
        current_roles = get_roles_for_user(str(user.id))
        # 删除所有当前角色
        for current_role in current_roles:
            remove_role_for_user(str(user.id), current_role)
        # 添加新角色
        add_role_for_user(str(user.id), role)
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.delete("/{user_id}", response_model=schemas.User)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除用户
    """
    # 检查权限
    if not deps.check_permissions("user", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    # 不能删除超级管理员
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")
    
    # 删除用户
    db.delete(user)
    db.commit()
    
    return user


@router.post("/import", response_model=Dict[str, Any])
def import_users(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
) -> Any:
    """
    批量导入用户
    """
    # 检查权限
    if not deps.check_permissions("user", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查文件类型
    if file.content_type not in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    ]:
        raise HTTPException(status_code=400, detail="只支持Excel或CSV文件")
    
    try:
        # 读取文件内容
        contents = file.file.read()
        buffer = io.BytesIO(contents)
        
        # 根据文件类型读取数据
        if file.content_type == "text/csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)
        
        # 验证必要的列
        required_columns = ["username", "ehr_id", "password", "name"]
        for column in required_columns:
            if column not in df.columns:
                raise HTTPException(
                    status_code=400, detail=f"缺少必要的列: {column}"
                )
        
        # 处理导入结果
        success_count = 0
        failed_users = []
        
        # 处理每一行数据
        for index, row in df.iterrows():
            try:
                # 检查用户名和EHR号是否已存在
                user_by_username = db.query(models.User).filter(models.User.username == row["username"]).first()
                user_by_ehr_id = db.query(models.User).filter(models.User.ehr_id == row["ehr_id"]).first()
                
                if user_by_username:
                    failed_users.append({
                        "row": index + 2,  # Excel行号从1开始，标题占一行
                        "username": row["username"],
                        "reason": "用户名已存在"
                    })
                    continue
                
                if user_by_ehr_id:
                    failed_users.append({
                        "row": index + 2,
                        "username": row["username"],
                        "reason": "EHR号已存在"
                    })
                    continue
                
                # 创建用户
                user = models.User(
                    username=row["username"],
                    ehr_id=row["ehr_id"],
                    hashed_password=get_password_hash(row["password"]),
                    name=row["name"],
                    department=row.get("department", ""),
                    is_active=True,
                    is_superuser=False,
                    team_id=None,
                    last_password_change=datetime.now()
                )
                
                # 添加团队（如果提供）
                if "team_id" in df.columns and not pd.isna(row["team_id"]):
                    team = db.query(models.Team).filter(models.Team.id == row["team_id"]).first()
                    if team:
                        user.team_id = team.id
                
                db.add(user)
                db.commit()
                db.refresh(user)
                
                # 添加角色（如果提供）
                if "role" in df.columns and not pd.isna(row["role"]):
                    add_role_for_user(str(user.id), row["role"])
                else:
                    # 默认角色为普通用户
                    add_role_for_user(str(user.id), "user")
                
                success_count += 1
                
            except Exception as e:
                failed_users.append({
                    "row": index + 2,
                    "username": row["username"] if "username" in row else "未知",
                    "reason": str(e)
                })
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_users),
            "failed_users": failed_users
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"导入用户时发生错误: {str(e)}"
        )
    finally:
        file.file.close()


@router.get("/me/permissions", response_model=List[str])
def read_user_permissions(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的权限列表
    """
    # 如果是超级管理员，拥有所有权限
    if current_user.is_superuser:
        return ["*:*"]
    
    # 获取用户角色
    roles = get_roles_for_user(str(current_user.id))
    
    # 获取所有角色的权限
    permissions = []
    for role in roles:
        role_permissions = get_permissions_for_role(role)
        for p in role_permissions:
            # p格式为 [role, resource, action]
            if len(p) >= 3:
                permission = f"{p[1]}:{p[2]}"
                if permission not in permissions:
                    permissions.append(permission)
    
    return permissions 