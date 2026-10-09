"""
portrait /templates 路由 (PRD §8.1 D1 批量导入 Excel 模板)

提供 3 类 Excel 模板下载 (按类型):
  - GET /portrait/templates/excel/training       培训记录 (5 必填 + 2 选填)
  - GET /portrait/templates/excel/entry-exit     出入境台账 (17 列, 模块 2.1 实现)
  - GET /portrait/templates/excel/drill          消防演练 (6 列, 模块 2.2 实现)

设计要点:
  - 模板文件由后端动态生成, 避免静态文件版本不一致
  - 表头使用中文 (与 PRD §8.1 字段说明对齐)
  - 内容示例放第一行 (帮助业务人员理解格式)
  - 文件名固定格式: {类型}_导入模板.xlsx
"""
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

# 延迟导入 openpyxl (避免 app 启动时强制依赖)
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    _OPENPYXL_AVAILABLE = True
except ImportError:
    _OPENPYXL_AVAILABLE = False

router = APIRouter()


def _build_workbook(headers: list[str], sample_row: list, sheet_name: str) -> bytes:
    """构造 Excel 工作簿. headers 中文表头, sample_row 示例行."""
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装, 无法生成模板")

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="D05A6E", end_color="D05A6E", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")

    # 表头
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    # 示例行
    if sample_row:
        for col_idx, value in enumerate(sample_row, start=1):
            cell = ws.cell(row=2, column=col_idx, value=value)
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # 列宽自适应
    for col_idx, header in enumerate(headers, start=1):
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = max(14, len(str(header)) * 2 + 4)

    # 冻结表头
    ws.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ============================================================================
# 培训记录模板 (5 必填 + 2 选填)
# ============================================================================
_TRAINING_HEADERS = ["EHR号", "培训名", "培训时间", "培训类型", "培训机构", "证书编号", "有效期"]
_TRAINING_SAMPLE = [
    "0000001",
    "反洗钱业务培训",
    "2026-03-15 09:00:00",
    "线上",
    "中国金融培训中心",
    "FXQ-2026-0001",
    "2029-03-15",
]


@router.get("/excel/training", summary="下载培训记录 Excel 模板")
def download_training_template():
    """PRD §8.1 D1 第 3 Tab 占位 - 培训记录批量导入模板"""
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")

    xlsx_bytes = _build_workbook(
        headers=_TRAINING_HEADERS,
        sample_row=_TRAINING_SAMPLE,
        sheet_name="培训记录",
    )
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="training_import_template.xlsx"'},
    )


# ============================================================================
# 出入境台账模板 (17 列, 模块 2.1 实现时启用)
# ============================================================================
_ENTRY_EXIT_HEADERS = [
    "姓名", "团队", "职务", "证照号", "出境原因", "目的地",
    "申请离境", "申请返回", "证照类别", "申请类型", "团队审批人",
    "实际出境", "实际返回", "年份", "组别", "备注", "EHR号",
]
_ENTRY_EXIT_SAMPLE = [
    "张三", "审核处理团队", "高级审核员", "E12345678",
    "公务出差", "中国香港",
    "2026-04-01 09:00:00", "2026-04-05 18:00:00",
    "护照", "公务", "李四",
    "", "",
    2026, "审核一组", "示例备注", "0000001",
]


@router.get("/excel/entry-exit", summary="下载出入境台账 Excel 模板")
def download_entry_exit_template():
    """PRD §8.1 D1 第 1 Tab - 出入境批量导入模板 (模块 2.1 实现时启用)"""
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")

    xlsx_bytes = _build_workbook(
        headers=_ENTRY_EXIT_HEADERS,
        sample_row=_ENTRY_EXIT_SAMPLE,
        sheet_name="出入境台账",
    )
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="entry_exit_import_template.xlsx"'},
    )


# ============================================================================
# 消防演练模板 (6 列, 模块 2.2 实现时启用)
# ============================================================================
_DRILL_HEADERS = ["活动日期", "演练类型", "地点", "EHR号", "姓名", "是否参与"]
_DRILL_SAMPLE = [
    "2026-05-12", "应急疏散", "总行办公大楼 1 楼大厅",
    "0000001", "系统管理员", "是",
]


@router.get("/excel/drill", summary="下载消防演练 Excel 模板")
def download_drill_template():
    """PRD §8.1 D1 第 2 Tab - 消防演练批量导入模板 (模块 2.2 实现时启用)"""
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")

    xlsx_bytes = _build_workbook(
        headers=_DRILL_HEADERS,
        sample_row=_DRILL_SAMPLE,
        sheet_name="消防演练",
    )
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="drill_import_template.xlsx"'},
    )