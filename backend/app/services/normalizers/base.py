"""清洗规则基类与值状态载体。

每条值在流水线中以 NormalizeResult 形态逐规则传递：
raw 永不被改写（审计/可疑清单用），value 是当前清洗值。
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class NormalizeResult:
    raw: str                    # 原始值，永不被改写
    value: Any = ""             # 当前清洗值，逐规则传递
    is_numeric: bool = False    # 是否已成功转为数值
    is_suspicious: bool = False # 是否判定为可疑（修不出/超范围/多值）
    note: str = ""              # 清洗轨迹，如 "大写金额:叁仟柒佰→3700"
    context: str = ""           # 抽取数字后残留的上下文文本（供单位词规则判断）


class BaseNormalizer:
    """规则实现契约：子类声明 type_name，实现 apply。

    后续新增规则只需两步：
    1. builtin/ 下新建文件，实现 BaseNormalizer 子类，标 @register；
    2. field_normalizers.json 对应栏位的 pipeline 里加一行 {"type": "新type"}。
    """
    type_name: str = ""

    def __init__(self, params: dict):
        self.params = params or {}

    def apply(self, r: NormalizeResult) -> NormalizeResult:
        raise NotImplementedError

    def _note(self, r: NormalizeResult, text: str) -> None:
        r.note = f"{r.note}|{text}" if r.note else text
