"""画像批量导入公共脚手架 (重构方案 Phase 3)

原先 4 个路由 (出入境/演练/培训/家访) 各抄一份完全相同的导入前置:
content-type 白名单 + pandas 延迟导入 + 读文件 + BytesIO + csv/excel 分支
(外加两份 console.table 式失败反馈差异)。本模块收口为单一实现。

行解析与业务校验仍留在各路由/service —— 那是领域逻辑, 不属于脚手架。
"""
import io
from typing import Optional

from fastapi import HTTPException, UploadFile

ALLOWED_IMPORT_CONTENT_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}


async def read_import_dataframe(file: UploadFile) -> "tuple":
    """校验类型 + 延迟导入 pandas + 读入并解析为 DataFrame。

    返回 (DataFrame, pd)。返回 pd 模块本身是为了让调用方复用
    pd.to_datetime 等工具时不必再触发一次延迟导入样板。
    """
    if file.content_type not in ALLOWED_IMPORT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")
    try:
        import pandas as pd
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"pandas 未安装, 无法解析 Excel: {exc}")

    contents = await file.read()
    buffer = io.BytesIO(contents)
    if file.content_type == "text/csv":
        return pd.read_csv(buffer), pd
    return pd.read_excel(buffer), pd


def read_import_dataframe_sync(file: UploadFile) -> "tuple":
    """同步版 (家访端点是同步 def —— 见该端点注释里 sync/async 线程池的坑)。"""
    if file.content_type not in ALLOWED_IMPORT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")
    try:
        import pandas as pd
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"pandas 未安装, 无法解析 Excel: {exc}")

    contents = file.file.read()
    buffer = io.BytesIO(contents)
    if file.content_type == "text/csv":
        return pd.read_csv(buffer), pd
    return pd.read_excel(buffer), pd


def require_columns(df, required: list, *, optional: Optional[set] = None) -> None:
    """必填列缺失 → 400 (可选列不报错)。"""
    optional = optional or set()
    missing = [c for c in required if c not in df.columns and c not in optional]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必填列: {', '.join(missing)}")
