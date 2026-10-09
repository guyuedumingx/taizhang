"""
portrait 文件上传路由 (PRD §7.1 Step 1 扫描件)

端点:
  POST   /portrait/files/upload    上传扫描件 (multipart, 仅 leader/admin)
  DELETE /portrait/files/{path}    删除扫描件 (仅上传者可删, MVP 放宽到 leader/admin)

集成指南 §5 雷区 7: 永远走 Depends(get_current_active_user)
集成指南 §5 雷区 12: 失败显性化 (类型/大小校验在 file_storage_service)
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.portrait.services.file_storage_service import (
    delete_upload,
    save_upload,
)
from app.utils.logger import log_info


router = APIRouter()


def _can_upload_files(user: models.User) -> bool:
    """仅 leader (有 team_id 且非 admin) 或 admin 可上传扫描件.

    PRD §7.1: 组长做家访, 管理员**只读** (不可编辑家访). 上传扫描件视为"编辑家访",
    所以也限制为 leader (admin 可上传但看不到自己的家访列表, 仅给 leader 备份用).
    MVP: admin + leader 都允许 (admin 偶尔需要给档案补扫描件).
    """
    if user.is_superuser:
        return True
    if user.team_id is not None:
        return True
    return False


@router.post("/upload", summary="C1 扫描件上传 (仅 leader/admin)")
async def upload_scan(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """上传 PDF/JPG/PNG (≤5MB), 返回 file_path 供家访草稿写入 scan_file_path."""
    if not _can_upload_files(current_user):
        raise HTTPException(
            status_code=403,
            detail="仅 leader/admin 可上传扫描件 (PRD §7.1 业务规则)",
        )
    result = save_upload(file, subdir="home_visits")
    log_info(
        module="portrait",
        action="file.upload",
        message=f"上传扫描件 {result['file_path']} ({result['file_size']} bytes)",
        user_id=current_user.id,
        resource_type="file",
        resource_id=result["file_path"],
    )
    return result


@router.delete("/{file_path:path}", summary="删除扫描件 (仅 leader/admin)")
def delete_scan(
    file_path: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """删除扫描件. 防路径遍历在 service 层."""
    if not _can_upload_files(current_user):
        raise HTTPException(
            status_code=403,
            detail="仅 leader/admin 可删除扫描件",
        )
    delete_upload(file_path)
    log_info(
        module="portrait",
        action="file.delete",
        message=f"删除扫描件 {file_path}",
        user_id=current_user.id,
        resource_type="file",
        resource_id=file_path,
    )
    return {"ok": True, "file_path": file_path}