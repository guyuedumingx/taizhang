"""去除所有空白字符（半角/全角空格、制表符、换行）。"""
import re

from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_WS_RE = re.compile(r"[\s\u3000]+")


@register
class StripWhitespaceNormalizer(BaseNormalizer):
    type_name = "strip_whitespace"

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        text = str(r.value)
        cleaned = _WS_RE.sub("", text)
        if cleaned != text:
            r.value = cleaned
            self._note(r, "去空白")
        return r
