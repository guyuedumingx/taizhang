"""中文大写金额解析（确定性文法转换，非启发式猜数）。

支持的要素：前缀(人民币/RMB/￥/¥)、数字字(大写为主，简体可配置容忍)、
位权字(拾佰仟)、节权字(万/亿)、货币单位(元/圆/块、角、分)、结尾字(整/正)。

解析失败（非法组合如"壹拾亿亿"、混入阿拉伯数字）返回失败，不猜数，
交由链尾 invalid_policy 处置。
"""
from typing import Optional

from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_DIGITS = {
    "零": 0, "〇": 0,
    "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5, "陆": 6, "柒": 7, "捌": 8, "玖": 9,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_LOWERCASE_DIGITS = set("一二三四五六七八九")
_POS = {"拾": 10, "十": 10, "佰": 100, "百": 100, "仟": 1000, "千": 1000}
_LOWERCASE_POS = set("十百千")
_SEC = {"万": 10 ** 4, "萬": 10 ** 4, "亿": 10 ** 8, "億": 10 ** 8}
_LOWERCASE_SEC = set("万亿")
_PREFIXES = ("人民币", "RMB", "rmb", "￥", "¥")
_YUAN = {"元", "圆", "块"}
_JIAO = {"角", "毛"}
_FEN = {"分"}


def parse_uppercase_amount(text: str, allow_lowercase: bool = True) -> Optional[float]:
    """解析中文大写金额，成功返回数值，失败返回 None。"""
    s = text.strip()
    for p in _PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
            break
    if not s:
        return None
    if not allow_lowercase:
        if (set(s) & _LOWERCASE_DIGITS) or (set(s) & _LOWERCASE_POS) or (set(s) & _LOWERCASE_SEC):
            return None
    if any(c.isdigit() for c in s):
        return None

    result = 0.0
    section = 0
    digit = 0
    decimal = 0.0
    met_yuan = False
    recognized = False

    for ch in s:
        if ch in _DIGITS:
            digit = _DIGITS[ch]
            recognized = True
        elif ch in _POS:
            section += (digit if digit else 1) * _POS[ch]
            digit = 0
            recognized = True
        elif ch in _SEC:
            # 节权字前无数值（如"壹拾亿亿"的第二个亿）→ 非法组合
            if section == 0 and digit == 0:
                return None
            result += (section + digit) * _SEC[ch]
            section = digit = 0
            recognized = True
        elif ch in _YUAN:
            result += section + digit
            section = digit = 0
            met_yuan = True
            recognized = True
        elif ch in _JIAO:
            decimal += digit * 0.1
            digit = 0
            recognized = True
        elif ch in _FEN:
            decimal += digit * 0.01
            digit = 0
            recognized = True
        elif ch in ("整", "正"):
            recognized = True
            break
        elif ch in ("零", "〇"):
            recognized = True  # 占位，跳过空段
        else:
            return None  # 未识别字符 → 不猜数

    if not recognized:
        return None
    if not met_yuan:
        result += section + digit
        if digit:  # 尾部悬空数字且无单位（如"伍"），不算合法金额
            if not decimal:
                return None
    return round(result + decimal, 6)


@register
class UppercaseAmountNormalizer(BaseNormalizer):
    type_name = "uppercase_amount"

    def __init__(self, params: dict):
        super().__init__(params)
        self.allow_lowercase = bool(self.params.get("allow_lowercase", True))

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if r.is_numeric:
            return r
        text = str(r.value).strip()
        if not text:
            return r
        parsed = parse_uppercase_amount(text, self.allow_lowercase)
        if parsed is None:
            # 解析失败不猜数，值原样传递，由后续规则或 invalid_policy 处置
            return r
        r.value = parsed
        r.is_numeric = True
        self._note(r, f"大写金额:{text}→{parsed:g}")
        return r
