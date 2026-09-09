"""
预校验服务:解析上传的 Excel,跑完整校验链,返回 ImportValidationReport。

校验顺序(与 V2 方案 §7 一致):
  ① 文件级:MIME / 表头匹配 / 行数阈值
  ② 逐行:
     a. 必填检查
     b. 清洗试跑(field_normalizers 配置了 pipeline 的字段)
     c. 类型检查(number / date)
     d. EHR 号格式预校验(7 位数字)
     e. 归属映射(team 反查 / created_by 反查)
     f. 重复检测(unique_keys 组合,库内 + 文件内)
     g. name 取值
  ③ 汇总报告

validate 与 commit 之间无状态;commit 时复用同一套解析+校验函数。
"""
import io
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import import_config_loader

logger = logging.getLogger(__name__)

# ---------- 清洗层降级 ----------
# 特殊栏位处理方案(清洗层)尚未实现,当前版本直接跳过清洗试跑。
# 等 field_normalizers 落地后,把下面 _try_clean_field 里的实现替换为真实清洗调用。
try:
    from app.core.field_normalizers import apply_pipeline, get_field_normalizers  # type: ignore
    _HAS_CLEANING_LAYER = True
except ImportError:
    _HAS_CLEANING_LAYER = False

    def get_field_normalizers():  # type: ignore
        return []

    def apply_pipeline(value, pipeline, policy):  # type: ignore
        return value

EHR_PATTERN = re.compile(r"^\d{7}$")

# 校验问题类型
ISSUE_MISSING_REQUIRED = "missing_required"
ISSUE_DUPLICATE = "duplicate"
ISSUE_TEAM_NOT_FOUND = "team_not_found"
ISSUE_USER_NOT_FOUND = "user_not_found"
ISSUE_UNCLEANABLE = "uncleanable_value"
ISSUE_TYPE_MISMATCH = "type_mismatch"
ISSUE_ROW_LIMIT = "row_limit_exceeded"

# 数据起始行(模板:1=表头, 2=hint, 3=示例, 4=数据)
DATA_START_ROW = 4


def _field_label(field: models.Field) -> str:
    return field.label or field.name


def _normalize_cell(value: Any) -> Any:
    """把 Excel 单元格值规整成可比较的形式"""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v != "" else None
    return value


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _parse_date(value: Any) -> Optional[str]:
    """返回 YYYY-MM-DD 字符串或 None"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        v = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
            try:
                return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


async def read_upload_file(file: UploadFile) -> bytes:
    """读取上传文件,做基础 MIME 检查"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    # openpyxl 只支持 xlsx;若文件名是 xls 直接拒绝
    filename = (file.filename or "").lower()
    if filename.endswith(".xls") and not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 格式,请使用系统提供的导入模板")
    return content


def load_workbook_rows(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    解析 xlsx,返回 (headers, rows)。
    以 Sheet 2(数据 Sheet)为准,跳过前 3 行(表头 / hint / 示例)。
    表头从第 1 行取。
    """
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法解析 Excel 文件:{exc}")

    if len(wb.sheetnames) < 2:
        raise HTTPException(status_code=400, detail="Excel 结构不符合导入模板:缺少「模板」Sheet")

    ws = wb[wb.sheetnames[1]]  # 第二个 Sheet 是数据 Sheet

    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not all_rows:
        raise HTTPException(status_code=400, detail="Excel 内容为空")

    header_row = all_rows[0]  # 第 1 行: 表头
    headers = [str(h).strip() if h is not None else "" for h in header_row]

    # 数据行:跳过 hint 行(第2行)和示例行(第3行)
    # 注意:openpyxl values_only 模式会截掉尾部全空列,导致列错位,
    # 所以这里按表头数量显式对齐,不足补 None
    data_rows = all_rows[3:]
    rows: List[Dict[str, Any]] = []
    n_cols = len(headers)
    for row_offset, values in enumerate(data_rows, start=4):
        values = list(values)[:n_cols] + [None] * max(0, n_cols - len(values))
        # 全空行跳过
        if all(_normalize_cell(v) is None for v in values):
            continue
        row_data = {headers[i]: _normalize_cell(values[i]) if i < len(values) else None
                    for i in range(len(headers)) if headers[i]}
        rows.append({"_row": row_offset, **row_data})

    return headers, rows


def _check_headers(
    headers: List[str],
    template: models.Template,
) -> List[Tuple[int, str, str, str]]:
    """校验表头是否匹配模板字段,返回问题列表"""
    issues = []
    expected = {_field_label(f) for f in template.fields}
    actual = {h for h in headers if h}
    missing = expected - actual
    extra = actual - expected
    if missing:
        issues.append((0, ISSUE_MISSING_REQUIRED, None,
                       f"缺少必需列: {', '.join(sorted(missing))}"))
    if extra:
        issues.append((0, "extra_column", None,
                       f"存在未知列(将被忽略): {', '.join(sorted(extra))}"))
    return issues


def _try_clean_field(
    field_label: str,
    raw_value: Any,
    normalizers_map: Dict[str, Any],
) -> Tuple[bool, Any, Optional[str]]:
    """
    对配置了 pipeline 的字段跑清洗。
    返回 (is_cleanable, clean_value, error_reason)
    """
    if raw_value is None:
        return True, None, None
    spec = normalizers_map.get(field_label)
    if not spec:
        return True, raw_value, None
    try:
        clean_value = apply_pipeline(raw_value, spec.pipeline, spec.policy)
        return True, clean_value, None
    except Exception as exc:
        return False, None, str(exc)


def validate_rows(
    db: Session,
    *,
    template: models.Template,
    cfg: Dict[str, Any],
    rows: List[Dict[str, Any]],
    existing_keys: Dict[str, int],
    fallback_team_id: Optional[int] = None,
) -> schemas.ImportValidationReport:
    """
    逐行校验,返回 ImportValidationReport。
    同时用于 validate(预览) 与 commit(二次校验),保证逻辑一致。
    """
    identity_team_field = import_config_loader.get_identity_field(cfg, "team")
    identity_user_field = import_config_loader.get_identity_field(cfg, "created_by")
    unique_keys: List[str] = cfg.get("unique_keys") or ["name"]
    name_field: Optional[str] = cfg.get("name_field")

    normalizers_map = {n.field_label: n for n in get_field_normalizers()}
    template_fields = {_field_label(f): f for f in template.fields}

    # 预加载 team / user 映射
    teams = {t.name: t.id for t in db.query(models.Team).all()}
    users_by_ehr = {u.ehr_id: u.id for u in db.query(models.User).all()
                    if getattr(u, "ehr_id", None)}

    issues: List[schemas.ImportIssue] = []
    cleanable_previews: List[CleanablePreview] = []
    seen_keys: Dict[str, int] = {}  # 文件内已见 unique_keys -> row
    importable_rows = 0
    cleanable_count = 0

    for row_data in rows:
        excel_row: int = row_data["_row"]
        row_issues: List[schemas.ImportIssue] = []
        row_cleanable: List[CleanablePreview] = []
        row_values: Dict[str, Any] = {k: v for k, v in row_data.items() if k != "_row"}

        # a. 必填检查
        for label, field in template_fields.items():
            if field.required and _normalize_cell(row_values.get(label)) is None:
                row_issues.append(schemas.ImportIssue(
                    row=excel_row,
                    type=ISSUE_MISSING_REQUIRED,
                    field=label,
                    raw=None,
                    reason="必填字段为空",
                ))

        # b. 清洗试跑 + c. 类型检查
        for label, field in template_fields.items():
            raw_value = row_values.get(label)
            ok, clean_value, err = _try_clean_field(label, raw_value, normalizers_map)
            if not ok:
                row_issues.append(schemas.ImportIssue(
                    row=excel_row,
                    type=ISSUE_UNCLEANABLE,
                    field=label,
                    raw=raw_value,
                    reason=err or "字段值无法清洗",
                ))
                continue
            # 可清洗且值有变化 → 记入预览
            if clean_value != raw_value:
                row_cleanable.append(CleanablePreview(
                    row=excel_row, field=label, raw=raw_value, clean=clean_value,
                ))
            # 后续校验用清洗后的值
            row_values[label] = clean_value

            # 类型检查
            if field.type == "number" and clean_value is not None:
                if _parse_number(clean_value) is None:
                    row_issues.append(schemas.ImportIssue(
                        row=excel_row,
                        type=ISSUE_TYPE_MISMATCH,
                        field=label,
                        raw=raw_value,
                        reason="数字字段格式错误",
                    ))
            elif field.type == "date" and clean_value is not None:
                if _parse_date(clean_value) is None:
                    row_issues.append(schemas.ImportIssue(
                        row=excel_row,
                        type=ISSUE_TYPE_MISMATCH,
                        field=label,
                        raw=raw_value,
                        reason="日期字段格式错误,应为 YYYY-MM-DD",
                    ))

        # d. EHR 号格式预校验 + DB 反查
        if identity_user_field:
            ehr_value = row_values.get(identity_user_field)
            if ehr_value is not None:
                ehr_str = str(ehr_value).strip()
                if not EHR_PATTERN.match(ehr_str):
                    row_issues.append(schemas.ImportIssue(
                        row=excel_row,
                        type=ISSUE_USER_NOT_FOUND,
                        field=identity_user_field,
                        raw=ehr_value,
                        reason="EHR 号格式错误,应为 7 位数字(如 1000001)",
                    ))
                elif ehr_str not in users_by_ehr:
                    row_issues.append(schemas.ImportIssue(
                        row=excel_row,
                        type=ISSUE_USER_NOT_FOUND,
                        field=identity_user_field,
                        raw=ehr_value,
                        reason=f"EHR 号 {ehr_str} 不存在或未登记",
                    ))

        # e. 归属映射
        team_id: Optional[int] = None
        if identity_team_field:
            team_name = row_values.get(identity_team_field)
            if team_name is not None:
                team_id = teams.get(str(team_name))
                if team_id is None:
                    if fallback_team_id is not None:
                        team_id = fallback_team_id
                    else:
                        row_issues.append(schemas.ImportIssue(
                            row=excel_row,
                            type=ISSUE_TEAM_NOT_FOUND,
                            field=identity_team_field,
                            raw=team_name,
                            reason="团队不存在,无法匹配",
                        ))

        # f. 重复检测(仅当该行无其它 blocking issue 时)
        key_parts = []
        key_ok = True
        for k in unique_keys:
            if k == "name":
                # name 取 name_field 或 data.name
                if name_field:
                    v = row_values.get(name_field)
                else:
                    v = row_values.get("name")
            else:
                v = row_values.get(k)
            if v is None:
                key_ok = False
                break
            key_parts.append(str(v))
        if key_ok:
            key_value = "||".join(key_parts)
            if key_value in existing_keys:
                row_issues.append(schemas.ImportIssue(
                    row=excel_row,
                    type=ISSUE_DUPLICATE,
                    field=", ".join(unique_keys),
                    raw=key_value,
                    reason=f"与库内已有台账 #{existing_keys[key_value]} 重复",
                ))
            elif key_value in seen_keys:
                row_issues.append(schemas.ImportIssue(
                    row=excel_row,
                    type=ISSUE_DUPLICATE,
                    field=", ".join(unique_keys),
                    raw=key_value,
                    reason=f"与文件内第 {seen_keys[key_value]} 行重复",
                ))
            else:
                seen_keys[key_value] = excel_row

        # 汇总
        if row_issues:
            issues.extend(row_issues)
        else:
            importable_rows += 1
            cleanable_previews.extend(row_cleanable)
            cleanable_count += len(row_cleanable)

    preview_batch_id = f"IMP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    return schemas.ImportValidationReport(
        template_id=template.id,
        template_name=template.name,
        preview_batch_id=preview_batch_id,
        total_rows=len(rows),
        importable_count=importable_rows,
        cleanable_count=cleanable_count,
        issues=issues,
        cleanable_previews=cleanable_previews,
    )


async def run_validation(
    db: Session,
    *,
    template_id: int,
    file: UploadFile,
    fallback_team_id: Optional[int] = None,
) -> schemas.ImportValidationReport:
    """validate 端点入口:读取文件 + 行数阈值 + 解析 + 校验"""
    template = crud.template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    cfg = import_config_loader.get_import_config_for_template(template.name) or {}

    content = await read_upload_file(file)
    headers, rows = load_workbook_rows(content)

    # 文件级: 行数阈值
    max_rows = int(cfg.get("max_rows") or 2000)
    warn_rows = int(cfg.get("warn_rows") or 5000)
    hard_limit = int(cfg.get("max_rows_hard_limit") or 5000)
    if len(rows) > hard_limit:
        raise HTTPException(
            status_code=400,
            detail=f"总行数 {len(rows)} 超过硬上限 {hard_limit},请拆分文件后分批导入",
        )

    # 表头校验
    header_issues = _check_headers(headers, template)

    existing_keys = crud.ledger.get_existing_unique_keys(
        db,
        template_id=template.id,
        key_fields=[k for k in (cfg.get("unique_keys") or ["name"]) if k != "name"],
    )

    report = validate_rows(
        db,
        template=template,
        cfg=cfg,
        rows=rows,
        existing_keys=existing_keys,
        fallback_team_id=fallback_team_id,
    )

    # 把表头问题塞到最前面
    for row, itype, field, reason in reversed(header_issues):
        report.issues.insert(0, schemas.ImportIssue(row=row, type=itype, field=field, raw=None, reason=reason))

    # 行数警告
    if len(rows) > max_rows:
        report.row_limit_warning = (
            f"总行数 {len(rows)} 超过建议阈值 {max_rows},"
            f"仍可导入,但建议拆分文件"
        )
    elif len(rows) > warn_rows:
        report.row_limit_warning = (
            f"总行数 {len(rows)} 超过警告阈值 {warn_rows},"
            f"建议拆分文件后再导入"
        )

    return report
