"""
导入配置加载器:启动时读取 ledger_import_config.json 到内存,支持 reload()。
加载与缓存模式照抄 auto_fill_trigger_loader.py。
"""
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CONFIG_CACHE: Optional[List[Dict[str, Any]]] = None


def _config_path() -> str:
    # BASE_DIR = backend/app,配置文件放在 backend/ledger_import_config.json
    return os.path.join(settings.BASE_DIR, "..", "ledger_import_config.json")


def load() -> List[Dict[str, Any]]:
    """读取 ledger_import_config.json,失败返回空列表"""
    path = _config_path()
    if not os.path.exists(path):
        logger.warning(f"导入配置文件不存在: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            configs = data.get("configs", [])
        else:
            configs = data
        if not isinstance(configs, list):
            logger.error("导入配置文件格式错误:期望顶层为列表或含 configs 列表")
            return []
        return configs
    except Exception as exc:
        logger.error(f"导入配置加载失败: {exc}")
        return []


def reload() -> int:
    """热重载,返回配置条数"""
    global _CONFIG_CACHE
    with _LOCK:
        _CONFIG_CACHE = load()
        logger.info(f"导入配置已重载,共 {len(_CONFIG_CACHE)} 条")
        return len(_CONFIG_CACHE)


def get_import_configs() -> List[Dict[str, Any]]:
    """获取内存中的配置(启动时自动加载)"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        reload()
    return _CONFIG_CACHE or []


def get_import_config_for_template(template_name: str) -> Optional[Dict[str, Any]]:
    """按模板名匹配配置"""
    for cfg in get_import_configs():
        if cfg.get("template_name") == template_name:
            return cfg
    return None


def get_identity_field(cfg: Dict[str, Any], key: str) -> Optional[str]:
    """从 identity_mapping 里取字段名,如 cfg['identity_mapping']['team'] -> '组别'"""
    mapping = cfg.get("identity_mapping") or {}
    value = mapping.get(key)
    return value if isinstance(value, str) else None
