"""清洗层单元测试：规则链编排 + 大写金额解析 + 脏数据模式全覆盖。"""
import pytest

from app.services.normalizers import run_pipeline, get_normalizer, registered_types
from app.services.normalizers.builtin.uppercase_amount import parse_uppercase_amount
from app.services.normalizers.builtin.fullwidth_to_half import fullwidth_to_half

# 与 field_normalizers.json 中「特殊业务台账/金额」一致的规则链
AMOUNT_PIPELINE = [
    {"type": "strip_whitespace"},
    {"type": "fullwidth_to_half"},
    {"type": "semantic_null", "words": ["无", "没有", "暂无", "N/A"], "as_value": 0},
    {"type": "uppercase_amount", "allow_lowercase": True},
    {"type": "remove_currency", "symbols": ["¥", "￥", "元", "$", "＄"]},
    {"type": "remove_thousands"},
    {"type": "extract_number"},
    {"type": "unit_multiplier", "mapping": {"万": 10000, "w": 10000, "W": 10000, "千": 1000, "k": 1000, "K": 1000}},
    {"type": "range_check", "min": 0, "max": 100000000, "out_of_range": "flag"},
]
INVALID_POLICY = {"action": "flag", "reason": "金额无法解析"}


def clean(raw):
    return run_pipeline(raw, AMOUNT_PIPELINE, INVALID_POLICY)


class TestUppercaseAmountParser:
    """文档 3.1.1 大写金额解析方法中的全部样例。"""

    @pytest.mark.parametrize("text,expected", [
        ("人民币叁仟柒佰元整", 3700),
        ("壹万贰仟叁佰肆拾伍元陆角柒分", 12345.67),
        ("拾伍元", 15),                # 拾开头隐含 1×10
        ("壹佰零伍元", 105),           # 零作占位
        ("壹佰伍拾元", 150),           # 省略零按位权补齐
        ("壹亿零贰拾万", 100200000),   # 节中间零跳过空段
        ("柒角伍分", 0.75),            # 无元的纯小数
        ("壹仟", 1000),                # 无货币单位
        ("零元", 0),
        ("一千二百", 1200),            # 简体小写容忍
        ("十五元", 15),
    ])
    def test_parse_ok(self, text, expected):
        assert parse_uppercase_amount(text) == expected

    @pytest.mark.parametrize("text", [
        "壹拾亿亿",      # 非法组合，不猜数
        "abc壹佰元",     # 未识别字符
        "123元",         # 混入阿拉伯数字，交给其他规则
        "",
    ])
    def test_parse_fail(self, text):
        assert parse_uppercase_amount(text) is None

    def test_lowercase_not_allowed(self):
        assert parse_uppercase_amount("一千二百", allow_lowercase=False) is None
        assert parse_uppercase_amount("壹仟", allow_lowercase=False) == 1000


class TestBuiltinRules:
    def test_registered_types(self):
        types = registered_types()
        for t in ["strip_whitespace", "fullwidth_to_half", "uppercase_amount",
                  "remove_currency", "remove_thousands", "extract_number",
                  "unit_multiplier", "semantic_null", "range_check"]:
            assert t in types

    def test_get_unknown_type_raises(self):
        with pytest.raises(KeyError):
            get_normalizer("not_exists", {})

    def test_fullwidth_helper(self):
        assert fullwidth_to_half("１２３ＡＢＣ（）") == "123ABC()"


class TestDirtyPatterns:
    """文档 3.1 乱填模式清单：清洗策略逐一验证。"""

    @pytest.mark.parametrize("raw,expected", [
        ("12345.67", 12345.67),           # 干净值
        (" 500 ", 500),                   # 空白
        ("1,234,567", 1234567),           # 千分位
        ("¥1000", 1000),                  # 货币符
        ("￥2500.50", 2500.5),
        ("3700元", 3700),
        ("100万", 1000000),               # 单位词
        ("3千", 3000),
        ("1.5k", 1500),
        ("200W", 2000000),
        ("约5000", 5000),                 # 修饰词
        ("5000左右", 5000),
        ("１２３４５", 12345),            # 全角
        ("无", 0),                        # 语义空值 → 0
        ("没有", 0),
        ("人民币叁仟柒佰元整", 3700),      # 大写金额（含节权，不得被单位换算重复放大）
        ("壹万贰仟叁佰肆拾伍元陆角柒分", 12345.67),
    ])
    def test_cleanable(self, raw, expected):
        r = clean(raw)
        assert r.is_numeric, f"raw={raw}, note={r.note}"
        assert not r.is_suspicious
        assert r.value == expected
        assert r.raw == raw  # 原始值永不被改写

    def test_negative_parsed_but_flagged_by_range(self):
        """会计负数能解析出 -500，但超出 min:0 被标记可疑（数值有效、聚合排除）。"""
        r = clean("(500)")
        assert r.is_numeric and r.value == -500
        assert r.is_suspicious

    @pytest.mark.parametrize("raw", [
        "100-200",     # 范围
        "500或600",    # 多值
        "见附件",      # 无法解析
        "-5",          # 越下界
        "999999999",   # 越上界
    ])
    def test_suspicious(self, raw):
        r = clean(raw)
        assert r.is_suspicious, f"raw={raw}, note={r.note}"

    def test_numeric_with_digits_in_text(self):
        # "abc123" 能提取出数值 123，不属于可疑
        r = clean("abc123")
        assert r.is_numeric and r.value == 123 and not r.is_suspicious

    def test_empty_and_none(self):
        assert clean("").is_suspicious
        assert clean(None).is_suspicious


class TestInvalidPolicy:
    def test_fallback(self):
        r = run_pipeline("无", [{"type": "extract_number"}],
                         {"action": "fallback", "fallback": 0})
        assert r.is_numeric and r.value == 0

    def test_raw_keeps_value(self):
        r = run_pipeline("abc", [{"type": "extract_number"}], {"action": "raw"})
        assert not r.is_numeric and not r.is_suspicious and r.value == "abc"

    def test_default_is_flag(self):
        r = run_pipeline("abc", [{"type": "extract_number"}], None)
        assert r.is_suspicious
