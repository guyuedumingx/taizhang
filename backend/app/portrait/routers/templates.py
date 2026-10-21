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
    "序号", "EHR号", "姓名", "团队", "职务", "证照号码", "出境原因", "目的地",
    "申请离境日期", "申请返回日期", "申请证照类别", "申请类型", "团队审批人",
    "实际出境日期", "实际返回日期", "出境年份", "组别", "备注",
]
_ENTRY_EXIT_SAMPLE = [
    1, "0000001", "张三", "审核处理团队", "高级审核员", "E12345678",
    "公务出差", "中国香港",
    "2026-04-01 09:00:00", "2026-04-05 18:00:00",
    "护照", "公务", "李四",
    "", "",
    2026, "审核一组", "示例备注",
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


# ============================================================================
# 家访明细模板 (F11, PRD 附录 B.4 的 14 列)
# ============================================================================
_HOME_VISIT_HEADERS = [
    "所属团队", "被家访人EHR号", "被家访人姓名", "岗位", "联系电话",
    "家访年度", "家访时间", "家访方式", "家访地址", "家访人员及岗位",
    "是否已家访", "备注", "序号", "家访记录表扫描件",
]
_HOME_VISIT_SAMPLE = [
    "审核处理团队", "0000001", "张三", "高级审核员", "13800000000",
    2026, "2026-05-12 14:30:00", "线下", "北京市西城区某某路 1 号",
    "1.李四，高级主管", "是", "本月例行家访", 1, "已提交",
]

# 导入端点必填列 (与 home_visits.py 的 _HOME_VISIT_REQUIRED_COLS 保持一致)
_HOME_VISIT_REQUIRED = [
    "所属团队", "被家访人EHR号", "被家访人姓名", "家访年度",
    "家访时间", "家访方式", "是否已家访", "家访记录表扫描件",
]


@router.get("/excel/home-visit", summary="下载家访明细 Excel 模板 (F11)")
def download_home_visit_template():
    """PRD 附录 B.4 家访明细表 14 列 - F11 批量导入模板

    「家访人员及岗位」列填了也会被忽略: 导入时一律按导入人(组长)重建, 保证
    visitor_info 里的签字人和实际家访人一致。列留着是为了跟业务实际表样对齐。
    """
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")

    xlsx_bytes = _build_workbook(
        headers=_HOME_VISIT_HEADERS,
        sample_row=_HOME_VISIT_SAMPLE,
        sheet_name="家访明细",
    )
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="home_visit_import_template.xlsx"'},
    )


# ============================================================================
# 员工导入模板 (2026-10-16 决策 2)
# ============================================================================
_USER_IMPORT_HEADERS = ["EHR号", "姓名", "组别", "初始密码"]
_USER_IMPORT_SAMPLE = [
    "0000001",
    "张三",
    "审核一组",
    "Ab3#efGh9",
]


@router.get("/excel/user-import", summary="下载员工导入 Excel 模板 (决策 2)")
def download_user_import_template():
    """员工批量导入模板 — 4 列全必填

    - EHR号: 7 位数字, 唯一, 也是登录标识 (登录走 EHR 号, 不是用户名)
    - 姓名: 与系统已有姓名不一致时整行失败, 不静默覆盖
    - 组别: 按**组名**匹配; 匹配不到整行失败, 请先在团队管理里建组
    - 初始密码: 管理员逐个填。必须同时含大写、小写、数字、特殊字符, 且 >=8 位。
      不合规整行失败并列出缺哪几项。首登强制改密 (is_first_login) 已实现。
    """
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")

    xlsx_bytes = _build_workbook(
        headers=_USER_IMPORT_HEADERS,
        sample_row=_USER_IMPORT_SAMPLE,
        sheet_name="员工导入",
    )
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="user_import_template.xlsx"'},
    )
