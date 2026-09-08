"""字段值清洗层：注册表 + 流水线引擎（配置驱动的可扩展架构）。

三层模型：
- 规则（插件）：builtin/ 下单一职责的 BaseNormalizer 子类，@register 即插即用；
- 配置（编排）：backend/field_normalizers.json 声明特殊栏位清单及各自规则链；
- 引擎：run_pipeline 按配置顺序执行规则链，收集清洗轨迹与可疑标记。

新增一种清洗方法只需：builtin/ 新建规则文件 + 配置 JSON 加一行，引擎零改动。
"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register, get_normalizer, registered_types
from app.services.normalizers.engine import run_pipeline
from app.services.normalizers.loader import (
    find_pipeline,
    get_template_pipelines,
    get_special_field_names,
    reload as reload_config,
)

# 导入内置规则完成注册（新增规则后在此追加一行）
from app.services.normalizers.builtin import (  # noqa: F401
    strip_whitespace,
    fullwidth_to_half,
    uppercase_amount,
    remove_currency,
    remove_thousands,
    extract_number,
    unit_multiplier,
    semantic_null,
    range_check,
)


def clean_value(template_name: str, field_name: str, raw_value):
    """按配置清洗单值。该栏位未配置规则链时返回 None。"""
    entry = find_pipeline(template_name, field_name)
    if not entry:
        return None
    return run_pipeline(raw_value, entry.get("pipeline"), entry.get("invalid_policy"))
