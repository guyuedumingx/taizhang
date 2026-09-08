"""
自动填充触发配置加载器：从 JSON 配置文件读取字段名→API 映射。
文件路径: backend/auto_fill_triggers.json
修改后重启服务（或调用 reload()）生效。
"""
import json
import os
from typing import Dict, List, Optional

# loader.py 位于 backend/app/core/，向上三级即 backend/
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE_DIR, "auto_fill_triggers.json")


class AutoFillTriggerItem:
    __slots__ = ("field_name", "api_url", "headers", "timeout", "retry_times", "enabled", "description")

    def __init__(self, data: dict):
        self.field_name: str = data["field_name"]
        self.api_url: str = data["api_url"]
        self.headers: Dict[str, str] = data.get("headers") or {}
        self.timeout: int = data.get("timeout", 5)
        self.retry_times: int = data.get("retry_times", 3)
        self.enabled: bool = data.get("enabled", True)
        self.description: str = data.get("description", "")


# 启动时加载一次，缓存在内存中
_cache: Optional[List[AutoFillTriggerItem]] = None


def _load() -> List[AutoFillTriggerItem]:
    global _cache
    if _cache is not None:
        return _cache
    items = []
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and "field_name" in entry and "api_url" in entry:
                    items.append(AutoFillTriggerItem(entry))
    except FileNotFoundError:
        pass
    except json.JSONDecodeError as e:
        print(f"[auto_fill_trigger_loader] 配置文件 JSON 格式错误: {e}")
    _cache = items
    return _cache


def get_all_triggers() -> List[AutoFillTriggerItem]:
    """返回所有启用的触发配置。"""
    return [t for t in _load() if t.enabled]


def get_trigger_by_field_name(field_name: str) -> Optional[AutoFillTriggerItem]:
    """按字段名查找启用的触发配置。"""
    for t in _load():
        if t.field_name == field_name and t.enabled:
            return t
    return None


def get_trigger_field_names() -> List[str]:
    """返回所有启用的触发字段名列表。"""
    return [t.field_name for t in _load() if t.enabled]


def reload():
    """重新从文件加载配置（可在外部调用实现热更新）。"""
    global _cache
    _cache = None
    return _load()
