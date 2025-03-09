from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, users, teams, roles, ledgers, templates, workflows, workflow_nodes, workflow_instances, approvals, logs, statistics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(teams.router, prefix="/teams", tags=["团队管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(ledgers.router, prefix="/ledgers", tags=["台账管理"])
api_router.include_router(templates.router, prefix="/templates", tags=["模板管理"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流管理"])
api_router.include_router(workflow_nodes.router, prefix="/workflow-nodes", tags=["工作流节点管理"])
api_router.include_router(workflow_instances.router, prefix="/workflow-instances", tags=["工作流实例管理"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["审批管理"])
api_router.include_router(logs.router, prefix="/logs", tags=["日志管理"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["统计分析"])

@api_router.get("/health", tags=["health"])
def health_check():
    """健康检查接口"""
    return {"status": "ok"}

@api_router.get("/test-token", tags=["test"])
def test_token():
    """测试接口，返回一个有效的访问令牌"""
    from app.core.security import create_access_token
    from datetime import timedelta
    
    # 创建一个有效期为30天的令牌
    access_token = create_access_token(
        data={"sub": "1", "roles": ["admin"]},
        expires_delta=timedelta(days=30)
    )
    
    return {"access_token": access_token, "token_type": "bearer"} 