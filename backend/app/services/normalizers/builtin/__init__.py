"""内置清洗规则库：每个文件一条规则，import 即完成注册。"""
from app.services.normalizers.builtin import strip_whitespace  # noqa: F401
from app.services.normalizers.builtin import fullwidth_to_half  # noqa: F401
from app.services.normalizers.builtin import uppercase_amount  # noqa: F401
from app.services.normalizers.builtin import remove_currency  # noqa: F401
from app.services.normalizers.builtin import remove_thousands  # noqa: F401
from app.services.normalizers.builtin import extract_number  # noqa: F401
from app.services.normalizers.builtin import unit_multiplier  # noqa: F401
from app.services.normalizers.builtin import semantic_null  # noqa: F401
from app.services.normalizers.builtin import range_check  # noqa: F401
