"""去除千分位分隔符（逗号、撇号）。"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register


@register
class RemoveThousandsNormalizer(BaseNormalizer):
    type_name = "remove_thousands"

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        text = str(r.value)
        cleaned = text.replace(",", "").replace("'", "")
        if cleaned != text:
            r.value = cleaned
            self._note(r, "去千分位")
        return r
