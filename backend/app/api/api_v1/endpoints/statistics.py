from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services.ledger_service import LedgerService
from app.services.statistics_service import StatisticsService
from app.services.team_service import TeamService
from app.services.template_service import TemplateService
from app.services.user_service import UserService
from app.schemas.statistics import OverviewResponse
from app.schemas.statistics_query import (
    LedgerQueryResponse,
    QueryField,
    StatisticsQueryRequest,
)
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

@router.post("/ledger-query", response_model=LedgerQueryResponse)
def ledger_query(
    query: StatisticsQueryRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    多维度台账汇总查询：跨模板、系统字段 + 模板字段组合筛选。
    特殊栏位走清洗层归一化，响应附带数据质量报告（清洗/可疑明细）。
    需 statistics:view 权限（默认不授予任何角色，按需在 casbin 中赋权）。
    """
    if not deps.check_permissions("statistics", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    return StatisticsService.query_ledgers(db, query)


@router.get("/query-fields", response_model=List[QueryField])
def query_fields(
    template_id: int = Query(..., description="模板ID"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定模板的字段列表（用于动态生成筛选条件）。
    has_pipeline 标记配置了清洗规则链的字段（前端渲染为数值范围筛选）。
    """
    if not deps.check_permissions("statistics", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    return StatisticsService.get_query_fields(db, template_id)


@router.post("/export", response_class=Response)
def export_ledger_query(
    query: StatisticsQueryRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出查询结果为 Excel。
    特殊栏位导出清洗后值，可疑数据单独一个 Sheet（需 statistics:view 权限）。
    """
    if not deps.check_permissions("statistics", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")

    file_data, filename, content_type = StatisticsService.export_query_results(db, query)
    from urllib.parse import quote
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(filename)}"',
        "Content-Type": content_type,
    }
    return Response(content=file_data.getvalue(), headers=headers)


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