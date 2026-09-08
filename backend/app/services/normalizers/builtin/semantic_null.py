"""语义空值处理（"无"、"没有" 等 → 按 fallback 值计或标记排除）。"""
from app.services.normalizers.base import BaseNormalizer, NormalizeResult
from app.services.normalizers.registry import register

_DEFAULT_WORDS = ["无", "没有", "暂无", "N/A", "NA", "/", "-"]


@register
class SemanticNullNormalizer(BaseNormalizer):
    type_name = "semantic_null"

    def __init__(self, params: dict):
        super().__init__(params)
        words = self.params.get("words", _DEFAULT_WORDS)
        self.words = {str(w).strip().lower() for w in words}
        # as_value: 转换值（如 0）；缺省 None → 标记可疑排除
        as_value = self.params.get("as_value")
        self.as_value = float(as_value) if as_value is not None else None

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        if r.is_numeric or r.is_suspicious:
            return r
        text = str(r.value).strip().lower()
        if text not in self.words:
            return r
        if self.as_value is not None:
            r.value = self.as_value
            r.is_numeric = True
            self._note(r, f"语义空值→{self.as_value:g}")
        else:
            r.is_suspicious = True
            self._note(r, f"语义空值:{str(r.value)},排除")
        return r
