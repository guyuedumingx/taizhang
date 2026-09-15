"""非人民币金额识别：命中外币标记的值标可疑，不参与人民币汇总（可导出可见）。

在规则链中置于去货币符之前——否则 $/美元 会被静默剥掉混入人民币合计。
人民币标记（¥/￥/元/人民币）不在标记清单内，正常放行。
"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_DEFAULT_FOREIGN_MARKERS = [
    "$", "usd", "美元", "美圆", "美金",
    "€", "eur", "欧元", "欧罗",
    "£", "gbp", "英镑",
    "日元", "jpy", "円", "日币",
    "港元", "港币", "hkd", "港纸",
    "krw", "韩元", "韩币",
    "aud", "澳元", "澳币",
    "cad", "加元",
    "sgd", "新加坡元", "新币",
    "ntd", "新台币", "台币",
]


@register
class CurrencyCheckNormalizer(BaseNormalizer):
    type_name = "currency_check"

    def __init__(self, params: dict):
        super().__init__(params)
        markers = self.params.get("foreign_markers", _DEFAULT_FOREIGN_MARKERS)
        # 统一按小写匹配（USD/usd 一视同仁，中文标记不受影响）
        self._markers = [m.lower() for m in markers]

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if r.is_numeric or r.is_suspicious:
            return r
        text = str(r.value)
        if not text:
            return r
        lowered = text.lower()
        for marker in self._markers:
            if marker and marker in lowered:
                r.is_suspicious = True
                self._note(r, f"非人民币金额:{text}")
                return r
        return r
