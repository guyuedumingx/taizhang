"""field_normalizers.json 加载器：启动加载 + 内存缓存 + reload 热更新。

配置文件路径：backend/field_normalizers.json
结构见该文件；特殊栏位清单（哪个模板的哪个字段走哪条规则链）全部在这里维护。
"""
import json
import os
import threading
from typing import Dict, List, Optional

# loader.py 位于 backend/app/services/normalizers/，向上四级即 backend/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_CONFIG_PATH = os.path.join(_BACKEND_DIR, "field_normalizers.json")

_cache: Optional[List[dict]] = None
_lock = threading.Lock()


def _load() -> List[dict]:
    global _cache
    with _lock:
        if _cache is not None:
            return _cache
        items: List[dict] = []
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict) and entry.get("field_name") and entry.get("template_name"):
                        # 启动即校验规则类型，配置笔误快速失败
                        for step in entry.get("pipeline") or []:
                            from app.services.normalizers.registry import get_normalizer
                            get_normalizer(step.get("type"), {})
                        items.append(entry)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
            print(f"[normalizer_loader] 配置文件 JSON 格式错误: {e}")
        _cache = items
        return _cache


def _match(entry: dict, template_name: str, field_name: str) -> bool:
    return (
        entry.get("template_name") in (template_name, "*")
        and entry.get("field_name") in (field_name, "*")
    )


def find_pipeline(template_name: Optional[str], field_name: str) -> Optional[dict]:
    """按 精确匹配 > 模板通配 > 字段通配 的顺序查找规则链配置。"""
    entries = _load()
    if not entries:
        return None
    tn = template_name or ""
    for entry in entries:  # 精确
        if entry.get("template_name") == tn and entry.get("field_name") == field_name:
            return entry
    for entry in entries:  # 该字段全局生效
        if entry.get("template_name") == "*" and entry.get("field_name") == field_name:
            return entry
    for entry in entries:  # 该模板任意字段
        if entry.get("template_name") == tn and entry.get("field_name") == "*":
            return entry
    return None


def get_template_pipelines(template_name: Optional[str]) -> Dict[str, dict]:
    """返回某模板名下所有生效的特殊栏位配置，key 为字段名。"""
    entries = _load()
    tn = template_name or ""
    exact: Dict[str, dict] = {}
    wildcard: Dict[str, dict] = {}
    for entry in entries:
        if entry.get("template_name") == tn:
            exact[entry["field_name"]] = entry
        elif entry.get("template_name") == "*":
            wildcard[entry["field_name"]] = entry
    merged = dict(wildcard)
    merged.update(exact)
    return merged


def get_special_field_names() -> List[str]:
    """所有配置过的字段名（提示用）。"""
    return [e.get("field_name", "") for e in _load()]


def reload() -> List[dict]:
    """重新从配置文件加载（热更新）。"""
    global _cache
    with _lock:
        _cache = None
    return _load()
