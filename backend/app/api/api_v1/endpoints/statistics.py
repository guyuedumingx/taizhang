from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services.ledger_service import LedgerService
from app.services.team_service import TeamService
from app.services.template_service import TemplateService
from app.services.user_service import UserService
from app.schemas.statistics import OverviewResponse
from app.db.session import get_pool_status

router = APIRouter()

@router.get("/overview", response_model=OverviewResponse)
def get_system_overview(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取系统概览数据
    """
    # 获取系统概览数据
    users = UserService.get_users_count(db)
    teams = TeamService.get_teams_count(db)
    ledgers = LedgerService.get_ledgers(db)
    templates = TemplateService.get_templates(db)
    return {
        "users_count": users,
        "teams_count": teams,
        "ledgers": ledgers,
        "templates": templates
    }

@router.get("/ledgers")
def get_ledgers_statistics(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账相关统计数据
    """
    return {"message": "台账统计数据"}

@router.get("/workflows")
def get_workflows_statistics(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取工作流相关统计数据
    """
    return {"message": "工作流统计数据"}

@router.get("/pool-status")
def get_pool_status_endpoint(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取数据库连接池状态信息
    用于监控和诊断数据库连接池性能
    
    仅限管理员或超级用户访问
    """
    # 检查权限：仅限超级用户或管理员
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问连接池状态"
        )
    
    return get_pool_status() 