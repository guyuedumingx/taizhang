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