"""
portrait /home-visits 路由 (PRD §C §9.1 P6)

集成指南 §3 阶段 4: portrait P6 家访审批流后端
集成指南 §5 雷区 7: 永远走 Depends

端点:
  POST   /home-visits                       创建家访草稿 (leader)
  GET    /home-visits                       列表 (admin/leader/user 按权限隔离)
  GET    /home-visits/{id}                  详情
  PUT    /home-visits/{id}                  更新草稿 (仅 draft)
  POST   /home-visits/{id}/submit           提交审批 (draft → pending)
  POST   /home-visits/{id}/cancel           撤回 (pending → cancelled, 仅本人)
  POST   /home-visits/{id}/approve          审批通过 (admin/current_approver)
  POST   /home-visits/{id}/reject           审批驳回 (必须 comment)
"""
from datetime import datetime
from io import BytesIO
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait import models as portrait_models  # noqa: F401 触发 ORM 注册
from app.portrait.schemas import (
    HomeVisit,
    HomeVisitApproveRequest,
    HomeVisitCreate,
    HomeVisitImportRow,
    HomeVisitImportSummary,
    HomeVisitListResponse,
    HomeVisitMatrix,
    HomeVisitRejectRequest,
    HomeVisitSubmitRequest,
    HomeVisitUpdate,
)
from app.portrait.routers.templates import (
    _HOME_VISIT_HEADERS,
    _HOME_VISIT_REQUIRED,
)
from app.portrait.services import home_visit_service


router = APIRouter()


def _serialize(record: portrait_models.HomeVisitRecord, db: Session) -> dict:
    """HomeVisitRecord ORM -> dict (含 visited_user / visitor_user / current_approver / co_visitor 字段)
    Rule 8: 复用 ORM + 显式字段映射

    C1 (PRD §7.1) 新增字段:
      - co_visitor_user_id / co_visitor_name (第二家访人)
      - scan_file_path / scan_file_url (扫描件)
      - team_name (固定"审核处理团队")
    """
    visited = (
        db.query(models.User).filter(models.User.id == record.visited_user_id).first()
    )
    visitor = (
        db.query(models.User).filter(models.User.id == record.visitor_user_id).first()
    )
    current_approver = None
    if record.current_approver_id:
        current_approver = (
            db.query(models.User).filter(models.User.id == record.current_approver_id).first()
        )
    co_visitor = None
    if record.co_visitor_user_id:
        co_visitor = (
            db.query(models.User).filter(models.User.id == record.co_visitor_user_id).first()
        )

    return {
        "id": record.id,
        "visited_user_id": record.visited_user_id,
        "visited_ehr_id": visited.ehr_id if visited else None,
        "visited_name": visited.name if visited else None,
        "visitor_user_id": record.visitor_user_id,
        "visitor_name": visitor.name if visitor else None,
        "visit_year": record.visit_year,
        "visit_time": record.visit_time,
        "visit_method": record.visit_method,
        "visit_address": record.visit_address,
        "visitor_info": record.visitor_info,
        "is_visited": record.is_visited,
        "visit_date": record.visit_date,
        "position": record.position,
        "contact_phone": record.contact_phone,
        "address": record.address,
        "mobile": record.mobile,
        "home_phone": record.home_phone,
        "family1_name": record.family1_name,
        "family1_relation": record.family1_relation,
        "family1_contact": record.family1_contact,
        "family1_work_unit": record.family1_work_unit,
        "family2_name": record.family2_name,
        "family2_relation": record.family2_relation,
        "family2_contact": record.family2_contact,
        "family2_work_unit": record.family2_work_unit,
        "feedback": record.feedback,
        "status": record.status,
        "current_approver_id": record.current_approver_id,
        "current_approver_name": current_approver.name if current_approver else None,
        "submitted_at": record.submitted_at,
        "completed_at": record.completed_at,
        # C1 新增 (PRD §7.1)
        "co_visitor_user_id": record.co_visitor_user_id,
        "co_visitor_name": co_visitor.name if co_visitor else None,
        "scan_file_path": record.scan_file_path,
        "scan_file_url": (
            f"/uploads/portrait/{record.scan_file_path}" if record.scan_file_path else None
        ),
        "team_name": record.team_name,
        "scan_status": record.scan_status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@router.post("", response_model=HomeVisit, summary="P6 组长创建家访草稿")
def create_home_visit(
    data: HomeVisitCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """组长创建家访草稿 (status=draft, 需 submit 提交审批)"""
    record = home_visit_service.create_draft(db, visitor=current_user, data=data)
    return _serialize(record, db)


@router.get("", response_model=HomeVisitListResponse, summary="P6 家访列表 (按角色隔离)")
def list_home_visits(
    db: Session = Depends(deps.get_db),
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(draft|pending|approved|rejected|cancelled)$"
    ),
    visit_year: Optional[int] = None,
    visited_ehr_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """列表 (admin 全, leader 本组, user 自己被家访)"""
    items = home_visit_service.list_visits(
        db,
        viewer=current_user,
        status_filter=status_filter,
        visit_year=visit_year,
        visited_ehr_id=visited_ehr_id,
        skip=skip,
        limit=limit,
    )

    list_items = []
    for r in items:
        visited = db.query(models.User).filter(models.User.id == r.visited_user_id).first()
        visitor = db.query(models.User).filter(models.User.id == r.visitor_user_id).first()
        approver = None
        if r.current_approver_id:
            approver = (
                db.query(models.User).filter(models.User.id == r.current_approver_id).first()
            )
        # C1: 第二家访人反查 (列表只显示 name)
        co_visitor = None
        if r.co_visitor_user_id:
            co_visitor = (
                db.query(models.User).filter(models.User.id == r.co_visitor_user_id).first()
            )
        from app.portrait.schemas.home_visit import HomeVisitListItem
        list_items.append(
            HomeVisitListItem(
                id=r.id,
                visited_ehr_id=visited.ehr_id if visited else "",
                visited_name=visited.name if visited else "",
                visit_year=r.visit_year,
                visit_time=r.visit_time,
                visit_method=r.visit_method,
                is_visited=r.is_visited,
                status=r.status,
                submitted_at=r.submitted_at,
                completed_at=r.completed_at,
                visitor_name=visitor.name if visitor else None,
                current_approver_name=approver.name if approver else None,
                # C1 新增
                co_visitor_name=co_visitor.name if co_visitor else None,
                team_name=r.team_name,
                has_scan=bool(r.scan_file_path),
                created_at=r.created_at,
            )
        )

    return HomeVisitListResponse(total=len(list_items), items=list_items)


# ============================================================================
# F12 家访年度矩阵 (PRD 附录 B.2)
# ============================================================================
# 注意: 这个端点必须注册在 "/{visit_id}" 之前, 否则 FastAPI 会把 "/matrix"
# 当成 visit_id 解析成 "matrix" 抛 422。声明顺序即匹配顺序。
@router.get("/matrix", response_model=HomeVisitMatrix, summary="F12 家访年度矩阵")
def home_visit_matrix(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    team_name: Optional[str] = Query(None, description="按团队筛选行"),
    include_pending: bool = Query(
        True, description="是否把审批中(pending)的记录也计入; 草稿/驳回/撤回一律不计"
    ),
):
    """行=员工, 列=年份, 单元格=该年具体家访日期 (B.2)。

    权限与列表同一套口径 (admin 全员 / 组长本组 / 员工仅自己), 复用 service 里的
    范围判断, 不另写一份。
    """
    return home_visit_service.matrix(
        db, viewer=current_user, team_name=team_name, include_pending=include_pending
    )


# ============================================================================
# 批量导出 Excel (PRD §7.2 / 附录 B.4 同一张 14 列表)
# ============================================================================
@router.get("/export", summary="家访批量导出 Excel")
def export_home_visits(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(draft|pending|approved|rejected|cancelled)$"
    ),
    visit_year: Optional[int] = None,
    visited_ehr_id: Optional[str] = None,
):
    """导出 家访明细表_YYYY-MM-DD_HHmm.xlsx, 列与 F11 导入模板一致 (B.4 的 14 列)。

    权限: PRD §13「家访批量导出 Excel — 员工 ❌ / 组长 ✅可见范围内 / 管理员 ✅全部」。

    ⚠️ 这里必须显式 403 拦普通员工, 不能只靠 list_for_export 的范围收口 ——
    那样普通员工虽然只能导出自己那几条, 但 PRD 写的是 ❌, 而且导出的表头带
    团队/岗位/电话, 属于台账性质的数据, 不该让员工拿到自己那条的完整行。
    """
    if not current_user.is_superuser and not current_user.team_id:
        raise HTTPException(
            status_code=403, detail="普通员工不可导出家访明细表 (PRD §13)"
        )
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"openpyxl 未安装: {exc}")

    records = home_visit_service.list_for_export(
        db,
        viewer=current_user,
        status_filter=status_filter,
        visit_year=visit_year,
        visited_ehr_id=visited_ehr_id,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "家访明细"
    for col, header in enumerate(_HOME_VISIT_HEADERS, start=1):
        ws.cell(row=1, column=col, value=header)
    ws.freeze_panes = "A2"

    for i, r in enumerate(records, start=1):
        visited = (
            db.query(models.User).filter(models.User.id == r.visited_user_id).first()
        )
        ws.append(
            [
                r.team_name,
                visited.ehr_id if visited else "",
                visited.name if visited else "",
                r.position or "",
                r.contact_phone or "",
                r.visit_year,
                r.visit_time,
                r.visit_method,
                r.visit_address or "",
                r.visitor_info or "",
                "是" if r.is_visited else "否",
                r.feedback or "",
                i,
                r.scan_status or "未提交",
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    # §7.2 指定文件名 家访明细表_YYYY-MM-DD_HHmm.xlsx
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    # 中文文件名走 RFC 5987 (filename*=UTF-8''...), 否则浏览器收到乱码名
    quoted = quote(f"家访明细表_{stamp}.xlsx")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=home_visit_{stamp}.xlsx; filename*=UTF-8''{quoted}"
            )
        },
    )


@router.get("/{visit_id}", response_model=HomeVisit, summary="P6 家访详情")
def get_home_visit(
    visit_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.get_visit(db, visit_id=visit_id, viewer=current_user)
    return _serialize(record, db)


@router.put("/{visit_id}", response_model=HomeVisit, summary="更新家访草稿 (仅 draft)")
def update_home_visit(
    visit_id: int,
    data: HomeVisitUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.get_visit(db, visit_id=visit_id, viewer=current_user)
    if record.visitor_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅创建人可更新草稿")
    if record.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"状态 {record.status} 不可编辑, 仅 draft 可编辑"
        )

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(record, k, v)
    record.updated_at = datetime.now()
    db.commit()
    db.refresh(record)
    return _serialize(record, db)


@router.post("/{visit_id}/submit", response_model=HomeVisit, summary="P6 提交审批 (draft → pending)")
def submit_home_visit(
    visit_id: int,
    data: HomeVisitSubmitRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.submit(
        db, visit_id=visit_id, viewer=current_user, next_approver_id=data.next_approver_id
    )
    return _serialize(record, db)


@router.post("/{visit_id}/cancel", response_model=HomeVisit, summary="P6 撤回 (pending → cancelled)")
def cancel_home_visit(
    visit_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.cancel(db, visit_id=visit_id, viewer=current_user)
    return _serialize(record, db)


@router.post("/{visit_id}/approve", response_model=HomeVisit, summary="P6 审批通过 (admin/current_approver)")
def approve_home_visit(
    visit_id: int,
    data: HomeVisitApproveRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.approve(
        db, visit_id=visit_id, viewer=current_user, comment=data.comment
    )
    return _serialize(record, db)


@router.post("/{visit_id}/reject", response_model=HomeVisit, summary="P6 审批驳回 (必须 comment)")
def reject_home_visit(
    visit_id: int,
    data: HomeVisitRejectRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    record = home_visit_service.reject(
        db, visit_id=visit_id, viewer=current_user, comment=data.comment
    )
    return _serialize(record, db)


# ============================================================================
# F11 批量导入 (PRD 附录 B.4 的 14 列)
# ============================================================================
def _parse_bool(value, default: bool = False) -> bool:
    """Excel 的"是/否"可能是 bool / '是' / 'YES' / 1 —— 全部归一, 不猜。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"是", "参与", "true", "1", "y", "yes"}:
        return True
    if s in {"否", "false", "0", "n", "no", ""}:
        return False
    raise ValueError(f"无法识别为布尔值: {value!r} (可用: 是/否)")


@router.post("/import", response_model=HomeVisitImportSummary, summary="F11 家访批量导入")
def import_home_visits(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """按 B.4 的 14 列批量导入家访记录 (仅组长, 限本组)。

    导入产出的记录 status=draft, 仍需走审批流 —— 导入不是审批通道。
    行解析失败与业务校验失败都进 failed_rows (Rule 12), 不静默丢行。

    端点是同步 def 而非 async: 本 router 其他端点全是同步, FastAPI 会把它们放到
    同一个线程池里跑, 依赖 session 与端点体不会跨线程并发操作同一个连接。
    async 端点会在另一个线程池线程里执行, 与依赖 session 并发使用同一连接。
    """
    if file.content_type not in {
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    }:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")
    try:
        import pandas as pd
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"pandas 未安装, 无法解析 Excel: {exc}")

    try:
        contents = file.file.read()
        buffer = BytesIO(contents)
        df = (
            pd.read_csv(buffer)
            if file.content_type == "text/csv"
            else pd.read_excel(buffer)
        )
        missing = [c for c in _HOME_VISIT_REQUIRED if c not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必填列: {', '.join(missing)} (模板见 GET /portrait/templates/excel/home-visit)",
            )

        rows: list[HomeVisitImportRow] = []
        parse_failures: list[dict] = []
        for idx, raw in df.iterrows():
            row_number = int(idx) + 2  # 1 = 表头, Excel 里从第 2 行开始
            ehr_raw = raw.get("被家访人EHR号")
            ehr_id = "" if ehr_raw is None or pd.isna(ehr_raw) else str(ehr_raw).strip()
            if ehr_raw is not None and not pd.isna(ehr_raw):
                # Excel 常把 7 位 EHR 读成数字, str(1903951.0) 会得到 "1903951.0"
                if ehr_id.endswith(".0"):
                    ehr_id = ehr_id[:-2]
            try:
                team = "" if pd.isna(raw.get("所属团队")) else str(raw["所属团队"]).strip()
                if team != "审核处理团队":
                    raise ValueError(
                        f'所属团队必须为 "审核处理团队", 收到: {team!r}'
                    )
                visit_time = pd.to_datetime(raw["家访时间"]).to_pydatetime()
                visit_year = int(raw["家访年度"])
                scan_status = (
                    "未提交"
                    if pd.isna(raw.get("家访记录表扫描件"))
                    else str(raw["家访记录表扫描件"]).strip()
                )
                rows.append(
                    HomeVisitImportRow(
                        row_number=row_number,
                        visited_ehr_id=ehr_id,
                        visited_full_name=(
                            "" if pd.isna(raw.get("被家访人姓名"))
                            else str(raw["被家访人姓名"]).strip()
                        ),
                        visited_job_title=None if pd.isna(raw.get("岗位")) else str(raw["岗位"]).strip(),
                        visited_phone=None if pd.isna(raw.get("联系电话")) else str(raw["联系电话"]).strip(),
                        visit_year=visit_year,
                        visit_time=visit_time,
                        visit_method=str(raw["家访方式"]).strip(),
                        visit_address=None if pd.isna(raw.get("家访地址")) else str(raw["家访地址"]).strip(),
                        is_visited=_parse_bool(raw["是否已家访"]),
                        remarks=None if pd.isna(raw.get("备注")) else str(raw["备注"]).strip(),
                        scan_status=scan_status,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — 单行解析失败不炸整个导入
                parse_failures.append(
                    {
                        "row_number": row_number,
                        "ehr_id": ehr_id,
                        "reason": f"行解析失败: {type(exc).__name__}: {exc}",
                    }
                )

        summary = home_visit_service.import_rows(db, importer=current_user, rows=rows)
        summary["failed_rows"].extend(parse_failures)
        summary["failed_count"] = len(summary["failed_rows"])
        return HomeVisitImportSummary(**summary)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {type(exc).__name__}: {exc}")