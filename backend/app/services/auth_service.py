from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.config import settings
from app.core.ehr_validator import validate_ehr_format
from app.core.login_throttle import login_throttle
from app.core.security import create_access_token, verify_password, get_password_hash
from app.services.casbin_service import get_roles_for_user, get_permissions_for_role, add_role_for_user

# 密码最长有效期 (天)。PRD §17.3: 90 天未改密视为过期。
PASSWORD_MAX_AGE_DAYS = 90


def _get_is_first_login(db: Session, user_id: int) -> bool:
    """读取 portrait_user_metadata.is_first_login. 行不存在时返回 False.

    行为:
      - 有 metadata 行 → 返回行的 is_first_login
      - 无 metadata 行 → 返回 False (兼容旧用户, 不强制改密)

    仅在创建新用户和首次注册时建 metadata 行 (is_first_login=True).
    """
    # 延迟导入避免循环依赖
    from app.portrait.models.user_metadata import PortraitUserMetadata
    meta = (
        db.query(PortraitUserMetadata)
        .filter(PortraitUserMetadata.user_id == user_id)
        .first()
    )
    return bool(meta.is_first_login) if meta else False


def _set_is_first_login(db: Session, user_id: int, value: bool) -> None:
    """更新或新建 portrait_user_metadata.is_first_login"""
    from app.portrait.models.user_metadata import PortraitUserMetadata
    meta = (
        db.query(PortraitUserMetadata)
        .filter(PortraitUserMetadata.user_id == user_id)
        .first()
    )
    if meta:
        meta.is_first_login = value
    else:
        db.add(PortraitUserMetadata(user_id=user_id, is_first_login=value))
    db.commit()


def get_password_change_requirement(db: Session, user: models.User) -> Optional[str]:
    """服务端强制改密判定 (重构方案 Phase 0: 评审 P0-1)。

    返回 None 表示不需要改密; 否则返回原因码, 由调用方转成 403:
      - "PASSWORD_CHANGE_REQUIRED": 首次登录未改密 (开关可控)
      - "PASSWORD_EXPIRED": 密码超过 90 天未修改 (PRD §17.3)

    之前该判定只在登录响应里带标志、由前端弹窗执行, 携合法 JWT 直接调
    API 即可绕过 —— 现在由 deps.get_current_user 在每个请求上强制。
    """
    if settings.FORCE_FIRST_LOGIN_PASSWORD_CHANGE and _get_is_first_login(db, user.id):
        return "PASSWORD_CHANGE_REQUIRED"
    if user.last_password_change:
        if datetime.now() - user.last_password_change > timedelta(days=PASSWORD_MAX_AGE_DAYS):
            return "PASSWORD_EXPIRED"
    return None


class AuthService:
    """认证服务类，处理用户认证相关的业务逻辑"""

    @staticmethod
    def authenticate_user(db: Session, ehr_id: str, password: str) -> Dict[str, Any]:
        """用户认证"""
        # PRD §3.2 + §17.3: 登录处统一拦截 EHR 格式 (恰好 7 位数字)
        try:
            validate_ehr_format(ehr_id)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"EHR号格式错误: {e}")

        # Phase 0 P0-2: 失败锁定检查 (在验密之前, 锁定期内不再消耗密码验证)
        login_throttle.check(ehr_id)

        # 使用EHR号查找用户
        user = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        if not user:
            login_throttle.record_failure(ehr_id)
            raise HTTPException(status_code=401, detail="EHR号或密码错误")
        if not verify_password(password, user.hashed_password):
            login_throttle.record_failure(ehr_id)
            raise HTTPException(status_code=401, detail="EHR号或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="用户已被禁用")

        login_throttle.record_success(ehr_id)

        # 获取用户角色
        roles = get_roles_for_user(str(user.id))

        # 检查密码是否过期 (90 天)
        password_expired = False
        if user.last_password_change:
            three_months_ago = datetime.now() - timedelta(days=90)
            password_expired = user.last_password_change < three_months_ago

        # 检查首次登录 (PRD §3.2: 默认管理员首次必须改密)
        is_first_login = _get_is_first_login(db, user.id)

        # 获取用户权限
        permissions = []
        for role in roles:
            role_permissions = get_permissions_for_role(role)
            for p in role_permissions:
                # p格式为 [role, resource, action]
                if len(p) >= 3:
                    permission = f"{p[1]}:{p[2]}"
                    if permission not in permissions:
                        permissions.append(permission)

        # 如果是超级管理员，添加所有权限
        if user.is_superuser:
            permissions = ["*:*"]

        access_token = create_access_token(
            data={"sub": str(user.id), "roles": roles}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "roles": roles,
            "password_expired": password_expired,
            "is_first_login": is_first_login,  # PRD §3.2 首次登录标志
            "permissions": permissions,
            "team_id": user.team_id
        }

    @staticmethod
    def register_user(db: Session, user_in: schemas.UserCreate) -> models.User:
        """注册新用户"""
        # Pydantic 已在 schema 层校验 EHR 格式, 此处业务唯一性检查
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

        # 创建新用户
        user = models.User(
            username=user_in.username,
            ehr_id=user_in.ehr_id,
            hashed_password=get_password_hash(user_in.password),
            name=user_in.name,
            department=user_in.department if user_in.department else "未分配",
            is_active=True,
            is_superuser=False,
            team_id=user_in.team_id,
            last_password_change=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 为新用户分配默认角色
        add_role_for_user(str(user.id), "user")

        # PRD §3.2: 新注册用户首次登录必须改密
        _set_is_first_login(db, user.id, True)

        return user

    @staticmethod
    def change_password(db: Session, user_id: int, password_data: schemas.PasswordChange) -> Dict[str, str]:
        """修改密码"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 验证旧密码
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码不正确")

        # 检查新密码是否与当前密码相同
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")

        # 设置新密码
        user.hashed_password = get_password_hash(password_data.new_password)
        user.last_password_change = datetime.now()
        db.commit()

        # PRD §3.2: 改密成功后清除首次登录标志
        _set_is_first_login(db, user_id, False)

        return {"message": "密码修改成功"}


auth_service = AuthService() 