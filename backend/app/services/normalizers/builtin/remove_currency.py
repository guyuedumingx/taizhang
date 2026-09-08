"""去除货币符号/货币单位字。"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_DEFAULT_SYMBOLS = ["¥", "￥", "元", "$", "＄"]


@register
class RemoveCurrencyNormalizer(BaseNormalizer):
    type_name = "remove_currency"

    def __init__(self, params: dict):
        super().__init__(params)
        self.symbols = [str(s) for s in self.params.get("symbols", _DEFAULT_SYMBOLS)]

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        text = str(r.value)
        cleaned = text
        for sym in self.symbols:
            cleaned = cleaned.replace(sym, "")
        if cleaned != text:
            r.value = cleaned
            self._note(r, "去货币符")
        return r
