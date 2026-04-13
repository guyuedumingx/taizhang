"""自动填充触发配置接口：从配置文件读取，提供查看和热重载功能。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.api import deps
from app.core.auto_fill_trigger_loader import get_all_triggers, reload

router = APIRouter()


@router.get("/", response_model=list)
def read_auto_fill_configs(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取当前自动填充触发配置列表（从配置文件读取）"""
    triggers = get_all_triggers()
    return [
        {
            "field_name": t.field_name,
            "api_url": t.api_url,
            "headers": t.headers,
            "timeout": t.timeout,
            "retry_times": t.retry_times,
            "enabled": t.enabled,
            "description": t.description,
        }
        for t in triggers
    ]


@router.post("/reload")
def reload_auto_fill_configs(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """重新从配置文件加载触发配置（修改 auto_fill_triggers.json 后调用，免重启）"""
    if not deps.check_permissions("template", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    items = reload()
    return {
        "success": True,
        "message": f"已重新加载，共 {len([t for t in items if t.enabled])} 条启用的配置",
    }
