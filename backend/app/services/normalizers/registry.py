"""规则注册表：type 字符串 → 规则类。"""
from typing import Dict, List, Type

from app.services.normalizers.base import BaseNormalizer

_registry: Dict[str, Type[BaseNormalizer]] = {}


def register(cls: Type[BaseNormalizer]) -> Type[BaseNormalizer]:
    if not cls.type_name:
        raise ValueError(f"{cls.__name__} 缺少 type_name，无法注册")
    _registry[cls.type_name] = cls
    return cls


def get_normalizer(type_name: str, params: dict = None) -> BaseNormalizer:
    if type_name not in _registry:
        raise KeyError(f"未注册的清洗规则类型: {type_name}")
    return _registry[type_name](params or {})


def registered_types() -> List[str]:
    return sorted(_registry)
