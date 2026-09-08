"""单位词乘数换算（100万 → 1000000）。

只依据 extract_number 残留的上下文文本判断单位词；context 为空时不动作——
绝不回看原始值，避免大写金额等已含节权的值被重复换算。
"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_DEFAULT_MAPPING = {"万": 10000, "w": 10000, "W": 10000, "千": 1000, "k": 1000, "K": 1000}


@register
class UnitMultiplierNormalizer(BaseNormalizer):
    type_name = "unit_multiplier"

    def __init__(self, params: dict):
        super().__init__(params)
        self.mapping = dict(_DEFAULT_MAPPING)
        self.mapping.update(self.params.get("mapping") or {})

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if not r.is_numeric:
            return r
        context = str(r.context or "").strip()
        if not context:
            return r
        for word, factor in self.mapping.items():
            if word and word in context:
                r.value = r.value * factor
                self._note(r, f"单位换算:×{factor:g}")
                break
        return r
