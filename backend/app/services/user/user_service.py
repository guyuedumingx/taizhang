from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
import pandas as pd
import io

from app import models, schemas
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, remove_role_for_user, get_roles_for_user


class UserService:
    """用户服务类，处理用户相关的业务逻辑"""

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
        """获取用户列表"""
        users = db.query(models.User).offset(skip).limit(limit).all()
        
        # 获取每个用户的角色
        for user in users:
            user.roles = get_roles_for_user(str(user.id))
        
        return users

    @staticmethod
    def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
        """创建新用户"""
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
            last_password_change=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 为用户分配角色
        if hasattr(user_in, 'roles') and user_in.roles:
            for role in user_in.roles:
                add_role_for_user(str(user.id), role)
        else:
            # 默认角色为普通用户
            add_role_for_user(str(user.id), "user")
        
        # 获取用户角色
        user.roles = get_roles_for_user(str(user.id))
        
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> models.User:
        """获取用户详情"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取用户角色
        user.roles = get_roles_for_user(str(user.id))
        
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, user_in: schemas.UserUpdate) -> models.User:
        """更新用户信息"""
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
            update_data["last_password_change"] = datetime.now()
        
        # 更新角色
        if "role" in update_data:
            role = update_data.pop("role")
            # 获取现有角色
            current_roles = get_roles_for_user(str(user.id))
            
            # 删除所有现有角色
            for r in current_roles:
                remove_role_for_user(str(user.id), r)
            
            # 添加新角色
            add_role_for_user(str(user.id), role)
        
        # 更新用户数据
        for key, value in update_data.items():
            setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        
        # 获取用户角色
        user.roles = get_roles_for_user(str(user.id))
        
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> models.User:
        """删除用户"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        db.delete(user)
        db.commit()
        
        return user

    @staticmethod
    def import_users_from_excel(db: Session, file: UploadFile) -> Dict[str, Any]:
        """从Excel文件导入用户"""
        try:
            contents = file.file.read()
            buffer = io.BytesIO(contents)
            df = pd.read_excel(buffer, engine='openpyxl')
            
            success_count = 0
            failed_count = 0
            error_messages = []
            
            for _, row in df.iterrows():
                try:
                    # 检查必要字段是否存在
                    if 'username' not in row or 'ehr_id' not in row or 'password' not in row or 'name' not in row:
                        failed_count += 1
                        error_messages.append(f"行数据缺少必要字段: {row}")
                        continue
                    
                    # 检查是否存在重复用户
                    existing_user = db.query(models.User).filter(
                        (models.User.username == row['username']) | 
                        (models.User.ehr_id == row['ehr_id'])
                    ).first()
                    
                    if existing_user:
                        failed_count += 1
                        error_messages.append(f"用户名或EHR号已存在: {row['username']}, {row['ehr_id']}")
                        continue
                    
                    # 创建用户
                    department = row.get('department', '未分配')
                    team_id = row.get('team_id')
                    
                    user = models.User(
                        username=row['username'],
                        ehr_id=row['ehr_id'],
                        hashed_password=get_password_hash(str(row['password'])),
                        name=row['name'],
                        department=department,
                        is_active=True,
                        is_superuser=False,
                        team_id=team_id if pd.notna(team_id) else None
                    )
                    
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    
                    # 分配角色
                    role = row.get('role', 'user')
                    add_role_for_user(str(user.id), str(role))
                    
                    success_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    error_messages.append(f"处理用户时出错: {row.get('username', 'Unknown')}, 错误: {str(e)}")
                    db.rollback()
            
            return {
                "success_count": success_count,
                "failed_count": failed_count,
                "error_messages": error_messages
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"处理Excel文件错误: {str(e)}")
        finally:
            file.file.close()

    @staticmethod
    def check_password_expired(user: models.User) -> Dict[str, Any]:
        """检查用户密码是否过期"""
        password_expired = False
        days_until_expiry = -1
        
        if user.last_password_change:
            three_months_ago = datetime.now() - timedelta(days=90)
            password_expired = user.last_password_change < three_months_ago
            
            if not password_expired:
                # 计算距离过期还有多少天
                days_until_expiry = (user.last_password_change + timedelta(days=90) - datetime.now()).days
        
        return {
            "password_expired": password_expired,
            "days_until_expiry": days_until_expiry,
            "last_password_change": user.last_password_change
        }


user_service = UserService() 