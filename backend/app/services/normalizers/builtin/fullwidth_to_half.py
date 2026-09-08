"""全角字符转半角（数字、字母、括号等可见字符）。"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register


def fullwidth_to_half(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:  # 全角空格
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


@register
class FullwidthToHalfNormalizer(BaseNormalizer):
    type_name = "fullwidth_to_half"

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        text = str(r.value)
        cleaned = fullwidth_to_half(text)
        if cleaned != text:
            r.value = cleaned
            self._note(r, "全角转半角")
        return r
