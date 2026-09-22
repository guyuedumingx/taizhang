"""
portrait 聚合 router (挂在 /portrait 前缀下)

集成指南 §3 阶段 4: 集中暴露 health + 子路由
集成指南 §5 雷区 7: 永远走 Depends
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait.routers import approvals as approvals_router
from app.portrait.routers import profiles as profiles_router
from app.portrait.routers import submissions as submissions_router


portrait_router = APIRouter()


@portrait_router.get("/health", tags=["portrait"], summary="健康检查")
def health():
    """无依赖的健康检查 (Rule 12: 不吞错)"""
    return {"status": "ok", "module": "portrait"}


@portrait_router.get("/me/permissions", tags=["portrait"], summary="当前用户的 portrait 权限")
def my_permissions(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """前端菜单用: 返回当前用户在 portrait 各资源的权限
    Rule 7: Python 显式判断 (与 service 层一致)
    """
    is_admin = bool(current_user.is_superuser)
    has_team = current_user.team_id is not None
    return {
        "user_id": current_user.id,
        "ehr_id": current_user.ehr_id,
        "is_admin": is_admin,
        "is_leader": has_team and not is_admin,
        "is_user": True,
        "permissions": {
            "portrait_all": ["*"] if is_admin else [],
            "portrait_self": ["read", "update", "create"] if True else [],
            "portrait_group": (
                ["read", "update", "create", "export"] if has_team else []
            ),
        },
    }


# 子路由
portrait_router.include_router(
    profiles_router.router, prefix="/profiles", tags=["portrait.档案"]
)
portrait_router.include_router(
    submissions_router.router, prefix="/submissions", tags=["portrait.提交"]
)
portrait_router.include_router(
    approvals_router.router, prefix="/approvals", tags=["portrait.审批"]
)