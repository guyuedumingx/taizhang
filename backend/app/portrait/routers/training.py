"""
portrait /training 路由 (PRD §10.3 占位)

端点:
  - GET  /training/me                          D2 员工只读
  - GET  /training/by-ehr/{ehr}                D2 跨人查看 (admin/leader)
  - POST /training                             管理员录入
  - POST /training/import                      批量导入 (管理员)
"""
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait.schemas import training as training_schema
from app.portrait.services import training_service

router = APIRouter()


def _serialize(rec) -> dict:
    return {
        "id": rec.id,
        "ehr_id": rec.ehr_id,
        "training_name": rec.training_name,
        "training_at": rec.training_at,
        "training_type": rec.training_type,
        "institution": rec.institution,
        "certificate_no": rec.certificate_no,
        "valid_until": rec.valid_until,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
    }


@router.get(
    "/me",
    response_model=List[training_schema.TrainingRecord],
    summary="D2 我的培训记录",
)
def list_my_training(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """员工查看自己的培训记录 (PRD §8.2 D2 占位)"""
    items = training_service.list_for_user(db, viewer=current_user, user_id=current_user.id)
    return [_serialize(r) for r in items]


@router.get(
    "/by-ehr/{ehr}",
    response_model=List[training_schema.TrainingRecord],
    summary="D2 跨人查看培训记录",
)
def list_training_by_ehr(
    ehr: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """管理员/组长查看指定员工的培训记录 (PRD §8.2 D2)"""
    items = training_service.list_by_ehr(db, viewer=current_user, ehr_id=ehr)
    return [_serialize(r) for r in items]


@router.post(
    "",
    response_model=training_schema.TrainingRecord,
    status_code=201,
    summary="管理员录入培训记录",
)
def create_training(
    data: training_schema.TrainingRecordCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """管理员手动补录培训记录 (D1 占位)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可录入培训记录")
    rec = training_service.create(db, data=data)
    return _serialize(rec)


# 模板列定义, 与 service 解析时校验
_TRAINING_REQUIRED_COLS = ["EHR号", "培训名", "培训时间", "培训类型", "培训机构"]
_TRAINING_OPTIONAL_COLS = ["证书编号", "有效期"]


@router.post(
    "/import",
    response_model=training_schema.TrainingImportSummary,
    summary="批量导入培训记录 (Excel)",
)
async def import_training(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
):
    """批量导入培训记录 (PRD §8.1 D1 第 3 Tab 占位)

    Excel 列 (5 必填 + 2 选填):
      1. EHR号   (必填, 7 位数字)
      2. 培训名   (必填)
      3. 培训时间 (必填, YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)
      4. 培训类型 (必填)
      5. 培训机构 (必填)
      6. 证书编号 (选填)
      7. 有效期   (选填, YYYY-MM-DD)

    权限: 仅管理员
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可批量导入培训记录")

    if file.content_type not in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    ]:
        raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 文件")

    # 延迟导入, 避免 app 启动时强制拉 pandas/openpyxl
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(status_code=500, detail="pandas 未安装, 无法解析 Excel")

    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        if file.content_type == "text/csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)

        for col in _TRAINING_REQUIRED_COLS:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"缺少必填列: {col}")

        valid_rows: list[training_schema.TrainingImportRow] = []
        parse_failures: list[dict] = []

        for idx, row in df.iterrows():
            row_number = int(idx) + 2  # Excel 行号 (1=标题)
            try:
                cert_no = None
                if "证书编号" in df.columns and not pd.isna(row.get("证书编号")):
                    cert_no = str(row["证书编号"]).strip()

                valid_until = None
                if "有效期" in df.columns and not pd.isna(row.get("有效期")):
                    valid_until = pd.to_datetime(row["有效期"]).date()

                valid_rows.append(
                    training_schema.TrainingImportRow(
                        row_number=row_number,
                        ehr_id=str(row["EHR号"]).strip(),
                        training_name=str(row["培训名"]).strip(),
                        training_at=pd.to_datetime(row["培训时间"]).to_pydatetime(),
                        training_type=str(row["培训类型"]).strip(),
                        institution=str(row["培训机构"]).strip(),
                        certificate_no=cert_no,
                        valid_until=valid_until,
                    )
                )
            except Exception as e:
                # 行解析失败: 进 failed_rows, 不入 service 入库
                parse_failures.append({
                    "row_number": row_number,
                    "ehr_id": str(row.get("EHR号", "")),
                    "reason": f"行解析失败: {type(e).__name__}: {e}",
                })

        summary = training_service.import_rows(db, rows=valid_rows)
        summary.failed_rows.extend(parse_failures)
        summary.failed_count = len(summary.failed_rows)
        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {type(e).__name__}: {e}")