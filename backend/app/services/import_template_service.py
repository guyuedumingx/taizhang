"""
导入模板下载服务:按模板 + 导入配置动态生成双 Sheet Excel。

Sheet 1: 填表说明
  - 标题段(导入流程 4 步)
  - 字段填写格式(优先 field.options.format_hint,降级为通用提示)
  - 必填标记

Sheet 2: {模板名}
  - 第 1 行: 表头(按 field_order 排,未列出的字段追加在后)
  - 第 2 行: format_hint + 必填标记
  - 第 3 行: 示例(灰色斜体,标注「示例,请删除后填写」)
  - select 字段:整列加 Excel 数据有效性下拉
"""
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app import crud, models
from app.core import import_config_loader

# 通用格式提示(当 field.options.format_hint 缺失时使用)
_GENERIC_HINTS = {
    "input": "文本",
    "textarea": "多行文本",
    "number": "数字",
    "date": "日期(YYYY-MM-DD)",
    "select": "从下拉框选择",
}

_EXAMPLE_ROW = 3
_HINT_ROW = 2
_HEADER_ROW = 1


def _field_label(field: models.Field) -> str:
    return field.label or field.name


def _format_hint(field: models.Field) -> str:
    options = field.options or {}
    hint = options.get("format_hint")
    if hint:
        return str(hint)
    return _GENERIC_HINTS.get(field.type, "按字段要求填写")


def _is_required(field: models.Field) -> bool:
    return bool(field.required)


def _ordered_fields(
    template: models.Template, field_order: List[str]
) -> List[models.Field]:
    """按 field_order 排字段,未列出的追加在后(保持模板原 order)"""
    label_to_field = {_field_label(f): f for f in template.fields}
    ordered: List[models.Field] = []
    seen = set()
    for label in field_order:
        f = label_to_field.get(label)
        if f and f.id not in seen:
            ordered.append(f)
            seen.add(f.id)
    rest = sorted(
        (f for f in template.fields if f.id not in seen),
        key=lambda x: (x.order or 0),
    )
    ordered.extend(rest)
    return ordered


def generate_import_template(db: Session, template_id: int) -> bytes:
    """生成双 Sheet 导入模板,返回 xlsx 二进制内容"""
    template = crud.template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    cfg = import_config_loader.get_import_config_for_template(template.name) or {}
    field_order = cfg.get("field_order") or []
    fields = _ordered_fields(template, field_order)

    if not fields:
        raise HTTPException(status_code=400, detail="模板未配置任何字段,无法生成导入模板")

    wb = Workbook()

    # ---------- Sheet 1: 填表说明 ----------
    ws_info = wb.active
    ws_info.title = "填表说明"

    title_font = Font(size=14, bold=True)
    section_font = Font(size=11, bold=True)
    normal_font = Font(size=10)

    ws_info["A1"] = f"{template.name} - 导入模板填写说明"
    ws_info["A1"].font = title_font
    ws_info.merge_cells("A1:D1")

    ws_info["A3"] = "导入流程:"
    ws_info["A3"].font = section_font
    steps = [
        "1. 在「台账管理 → 导入」页面选择本模板,下载本 Excel。",
        "2. 切换到第二个 Sheet「模板」,在第 4 行开始填写数据(第 3 行是示例,请删除)。",
        "3. 回到系统导入页面,选择本模板并上传填好的 Excel。",
        "4. 系统会先做预校验,确认无误后点「确认导入」才会真正写入。",
    ]
    for i, s in enumerate(steps, start=4):
        ws_info.cell(row=i, column=1, value=s).font = normal_font

    start_row = 4 + len(steps) + 1
    ws_info.cell(row=start_row, column=1, value="字段填写格式:").font = section_font
    header_font = Font(size=10, bold=True)
    ws_info.cell(row=start_row + 1, column=1, value="字段名").font = header_font
    ws_info.cell(row=start_row + 1, column=2, value="是否必填").font = header_font
    ws_info.cell(row=start_row + 1, column=3, value="格式要求").font = header_font

    for idx, field in enumerate(fields, start=start_row + 2):
        ws_info.cell(row=idx, column=1, value=_field_label(field)).font = normal_font
        ws_info.cell(row=idx, column=2, value="必填" if _is_required(field) else "选填").font = normal_font
        ws_info.cell(row=idx, column=3, value=_format_hint(field)).font = normal_font

    ws_info.column_dimensions["A"].width = 24
    ws_info.column_dimensions["B"].width = 12
    ws_info.column_dimensions["C"].width = 48

    # ---------- Sheet 2: 模板 ----------
    ws = wb.create_sheet(title=template.name[:31])  # Excel sheet 名最长 31 字符

    header_font = Font(bold=True, size=11)
    header_fill = PatternFill("solid", fgColor="DDEBF7")
    hint_font = Font(size=9, italic=True, color="808080")
    example_font = Font(size=10, italic=True, color="A0A0A0")

    # 第 1 行: 表头
    for col_idx, field in enumerate(fields, start=1):
        cell = ws.cell(row=_HEADER_ROW, column=col_idx, value=_field_label(field))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 第 2 行: format_hint + 必填标记
    for col_idx, field in enumerate(fields, start=1):
        required_mark = "必填;" if _is_required(field) else "选填;"
        cell = ws.cell(
            row=_HINT_ROW,
            column=col_idx,
            value=f"{required_mark} {_format_hint(field)}",
        )
        cell.font = hint_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 第 3 行: 示例
    example_values: Dict[str, Any] = {}
    cfg_example = cfg.get("example_row") or {}
    for col_idx, field in enumerate(fields, start=1):
        label = _field_label(field)
        value = cfg_example.get(label)
        if value is None:
            if field.type == "select":
                options = (field.options or {}).get("options") or []
                value = options[0] if options else ""
            elif field.type == "number":
                value = 100
            elif field.type == "date":
                value = datetime.now().strftime("%Y-%m-%d")
            else:
                value = f"示例{label}"
        cell = ws.cell(row=_EXAMPLE_ROW, column=col_idx, value=value)
        cell.font = example_font
        example_values[label] = value

    ws.cell(row=_EXAMPLE_ROW, column=len(fields) + 1, value="示例行,请删除后从下一行开始填写")
    ws.cell(row=_EXAMPLE_ROW, column=len(fields) + 1).font = example_font

    # 列宽
    for col_idx, field in enumerate(fields, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(
            14, len(_field_label(field)) * 3 + 6
        )

    # select 字段:数据有效性下拉(覆盖第 4 行到 max_rows,预留足够行数)
    max_rows = int(cfg.get("max_rows") or 2000)
    select_end_row = _EXAMPLE_ROW + max_rows
    for col_idx, field in enumerate(fields, start=1):
        if field.type != "select":
            continue
        options = (field.options or {}).get("options") or []
        if not options:
            continue
        # Excel 数据有效性公式长度上限约 255,选项过多时截断提示
        formula = '"' + ",".join(str(o) for o in options) + '"'
        if len(formula) > 250:
            continue  # 选项太多,放弃下拉,靠后端校验兜底
        dv = DataValidation(
            type="list",
            formula1=formula,
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="取值不合法",
            error="请从下拉框中选择",
        )
        col_letter = get_column_letter(col_idx)
        dv.add(f"{col_letter}{_EXAMPLE_ROW + 1}:{col_letter}{select_end_row}")
        ws.add_data_validation(dv)

    # number 字段:数值格式
    for col_idx, field in enumerate(fields, start=1):
        if field.type == "number":
            col_letter = get_column_letter(col_idx)
            for row_idx in range(_EXAMPLE_ROW + 1, select_end_row + 1):
                ws[f"{col_letter}{row_idx}"].number_format = "#,##0.00"

    # 冻结表头
    ws.freeze_panes = "A4"

    # 输出
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
