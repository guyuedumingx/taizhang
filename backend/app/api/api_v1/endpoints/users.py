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
from app.services.user.user_service import UserService as user_service

router = APIRouter()


@router.get("/", response_model=schemas.PaginatedResponse[schemas.User])
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
    total = db.query(models.User).count()
    
    # 获取每个用户的角色
    for user in users:
        user.roles = get_roles_for_user(str(user.id))
    
    return {
        "items": users,
        "total": total,
        "page": skip // limit + 1,
        "size": limit
    }


@router.post("/", response_model=schemas.User, status_code=201)
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
    
    # 使用用户服务创建用户
    user = user_service.create_user(db, user_in=user_in)
    
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
    
    # 使用用户服务更新用户
    return user_service.update_user(db, user_id=user_id, user_in=user_in)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    删除用户
    """
    # 检查权限
    if not deps.check_permissions("user", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    # 使用用户服务删除用户
    user_service.delete_user(db, user_id=user_id)


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