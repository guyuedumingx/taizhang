"""从文本中抽取数字。

- 恰好一个数字 → 转为数值，is_numeric=True，残留文本记入 context；
- 无数字 → 原样传递（由链尾 invalid_policy 处置）；
- 多个数字（"100-200"、"500或600"）→ 不可修，标记可疑。
- 会计负数 "(500)" → -500。
"""
import re

from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_PAREN_NEG_RE = re.compile(r"^\(([^)]*)\)$")


@register
class ExtractNumberNormalizer(BaseNormalizer):
    type_name = "extract_number"

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if r.is_numeric:
            return r
        text = str(r.value).strip()
        if not text:
            return r

        negative = False
        m = _PAREN_NEG_RE.match(text)
        if m:
            text = m.group(1)
            negative = True

        tokens = _NUM_RE.findall(text)
        if not tokens:
            return r
        if len(tokens) > 1:
            r.is_suspicious = True
            self._note(r, f"多值/范围,无法确定:{str(r.value)}")
            return r

        value = float(tokens[0])
        if negative:
            value = -value
        r.value = value
        r.is_numeric = True
        r.context = text.replace(tokens[0], "", 1)
        self._note(r, f"提取数字:{tokens[0]}")
        return r
