"""流水线引擎：按配置顺序执行规则链 + 链尾 invalid_policy 兜底。引擎本身永不因新规则而改动。"""
from typing import Any, List, Optional

from app.services.normalizers.base import NormalizeResult
from app.services.normalizers.registry import get_normalizer


def run_pipeline(
    raw_value: Any,
    pipeline: Optional[List[dict]] = None,
    invalid_policy: Optional[dict] = None,
) -> NormalizeResult:
    """对单个原始值执行清洗规则链，返回 NormalizeResult。

    invalid_policy（链尾兜底，决定整条链跑完仍未得到数值时的处置）：
    - flag:     标记可疑，不参与聚合（默认）
    - fallback: 按 fallback 值计算（如 无→0）
    - raw:      原样保留
    """
    r = NormalizeResult(raw=str(raw_value) if raw_value is not None else "", value=raw_value)
    if r.raw == "" and raw_value is None:
        r.value = ""

    for step in pipeline or []:
        type_name = step.get("type")
        params = {k: v for k, v in step.items() if k != "type"}
        normalizer = get_normalizer(type_name, params)
        r = normalizer.apply(r)
        if r.is_suspicious:
            break

    if not r.is_numeric and not r.is_suspicious:
        action = (invalid_policy or {}).get("action", "flag")
        if action == "flag":
            r.is_suspicious = True
            reason = (invalid_policy or {}).get("reason", "无法解析为数值")
            r.note = f"{r.note}|{reason}" if r.note else reason
        elif action == "fallback":
            fb = (invalid_policy or {}).get("fallback")
            if fb is None:
                r.is_suspicious = True
                r.note = (r.note + "|") if r.note else ""
                r.note += "invalid_policy.fallback 未配置"
            else:
                r.value = float(fb)
                r.is_numeric = True
                r.note = f"{r.note}|fallback→{fb:g}" if r.note else f"fallback→{fb:g}"
        # raw: 原样保留，什么都不做
    return r
