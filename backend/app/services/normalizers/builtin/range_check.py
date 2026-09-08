"""数值范围检查，越界按配置处置（flag 标可疑 / fallback 置换值 / clamp 截断）。"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register


@register
class RangeCheckNormalizer(BaseNormalizer):
    type_name = "range_check"

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if not r.is_numeric or r.is_suspicious:
            return r
        min_v = self.params.get("min")
        max_v = self.params.get("max")
        value = r.value
        in_range = True
        if min_v is not None and value < float(min_v):
            in_range = False
        if max_v is not None and value > float(max_v):
            in_range = False
        if in_range:
            return r

        action = self.params.get("out_of_range", "flag")
        if action == "fallback":
            fb = self.params.get("fallback_value")
            if fb is not None:
                r.value = float(fb)
                self._note(r, f"越界{value:g}→fallback {fb:g}")
                return r
        elif action == "clamp":
            if max_v is not None and value > float(max_v):
                r.value = float(max_v)
            if min_v is not None and r.value < float(min_v):
                r.value = float(min_v)
            self._note(r, f"越界截断:{value:g}→{r.value:g}")
            return r
        r.is_suspicious = True
        self._note(r, f"越界:{value:g} 不在 [{min_v}, {max_v}]")
        return r
