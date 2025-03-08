from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, users, teams, roles, ledgers, templates, workflows, approvals, logs

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(teams.router, prefix="/teams", tags=["团队管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(ledgers.router, prefix="/ledgers", tags=["台账管理"])
api_router.include_router(templates.router, prefix="/templates", tags=["模板管理"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流管理"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["审批管理"])
api_router.include_router(logs.router, prefix="/logs", tags=["日志管理"])

@api_router.get("/health", tags=["health"])
def health_check():
    """健康检查接口"""
    return {"status": "ok"} 