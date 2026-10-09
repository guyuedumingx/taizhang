"""
portrait 文件存储 service (PRD §7.1 Step 1 扫描件基建)

职责:
  - save_upload(file, subdir) -> dict(file_path, file_url, file_size, original_name)
  - delete_upload(rel_path)
  - 防路径遍历 (路径含 ".." 或绝对路径直接 400)

存储布局:
  backend/uploads/portrait/{subdir}/{year}/{uuid4_hex}.{ext}
  → 静态 URL: /uploads/portrait/{subdir}/{year}/{uuid4_hex}.{ext}

集成指南 §5 雷区 12: 失败显性化 (类型/大小不合法直接抛 HTTPException)
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile


# backend/uploads/portrait/
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads" / "portrait"

MAX_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg", ".png"}

_EXT_BY_TYPE = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def save_upload(file: UploadFile, *, subdir: str) -> dict:
    """落盘上传文件, 返回元数据.

    Args:
        file: FastAPI UploadFile
        subdir: 子目录名 (e.g. "home_visits")

    Returns:
        dict: { file_path, file_url, file_size, original_name }

    Raises:
        HTTPException 400: 类型不合法 / 超过 5MB
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type!r}, 仅允许 pdf/jpg/png",
        )
    contents = file.file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件 {len(contents) // 1024} KB 超过 5MB 上限 ({MAX_SIZE // 1024 // 1024}MB)",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="空文件, 拒绝保存")

    ext = _EXT_BY_TYPE[file.content_type]
    year = datetime.now().year
    rel_dir = Path(subdir) / str(year)
    abs_dir = UPLOAD_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    fname = f"{uuid.uuid4().hex}{ext}"
    abs_path = abs_dir / fname
    abs_path.write_bytes(contents)

    rel_path = str(rel_dir / fname).replace("\\", "/")
    return {
        "file_path": rel_path,
        "file_url": f"/uploads/portrait/{rel_path}",
        "file_size": len(contents),
        "original_name": file.filename or fname,
    }


def delete_upload(rel_path: str) -> None:
    """删除上传文件 (仅限 UPLOAD_ROOT 内部路径, 防路径遍历)."""
    if ".." in rel_path or rel_path.startswith("/") or "\\..\\" in rel_path:
        raise HTTPException(status_code=400, detail="非法路径 (防路径遍历)")
    abs_path = (UPLOAD_ROOT / rel_path).resolve()
    # 二次校验: 解析后仍必须在 UPLOAD_ROOT 之下
    if UPLOAD_ROOT.resolve() not in abs_path.parents:
        raise HTTPException(status_code=400, detail="非法路径 (超出上传根目录)")
    if abs_path.exists():
        abs_path.unlink()


def ensure_upload_root() -> Path:
    """确保上传根目录存在 (main.py 启动时调用)."""
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOAD_ROOT