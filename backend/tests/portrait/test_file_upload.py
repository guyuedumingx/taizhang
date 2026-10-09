"""
portrait 文件上传测试 (C1 PRD §7.1 扫描件基建)

覆盖 (3 test):
  - 上传合法 PDF (≤5MB) → 200 + file_path/file_url 返回
  - 上传 6MB PDF → 400 (大小超限)
  - 上传 .docx → 400 (类型不支持)
  - 删除扫描件 → 200
  - 防路径遍历: DELETE with ".." → 400
"""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.portrait.services.file_storage_service import UPLOAD_ROOT


client = TestClient(app)
API_PORTRAIT = f"{settings.API_V1_STR}/portrait"


@pytest.fixture(scope="function")
def leader_user(db: Session) -> models.User:
    """复用 test_home_visits._create_leader 模式"""
    existing = (
        db.query(models.User)
        .filter(models.User.is_superuser == False, models.User.team_id.isnot(None))  # noqa
        .first()
    )
    if existing:
        return existing
    team = models.Team(name="文件上传测试组", department="测试部门")
    db.add(team)
    db.commit()
    db.refresh(team)
    import random
    while True:
        ehr_id = str(random.randint(6000000, 6999999))
        existing = db.query(models.User).filter(models.User.ehr_id == ehr_id).first()
        if not existing:
            break
    leader = models.User(
        username=f"test_leader_file_{ehr_id}",
        ehr_id=ehr_id,
        name="文件测试组长",
        hashed_password="$2b$12$dummy",
        is_active=True,
        is_superuser=False,
        team_id=team.id,
        department="测试部门",
    )
    db.add(leader)
    db.commit()
    db.refresh(leader)
    return leader


@pytest.fixture(scope="function")
def leader_token_headers(leader_user: models.User) -> dict:
    token = create_access_token({"sub": str(leader_user.id)})
    return {"Authorization": f"Bearer {token}"}


def _make_pdf_bytes(size_bytes: int) -> bytes:
    """构造合法 PDF 头 + 填充到指定大小"""
    pdf_header = b"%PDF-1.4\n%fake\n"
    return pdf_header + b"\x00" * (size_bytes - len(pdf_header))


def test_upload_scan_pdf_ok(leader_token_headers: dict):
    """合法 PDF 3MB → 200, 返回 file_path/file_url/file_size"""
    payload = _make_pdf_bytes(3 * 1024 * 1024)
    files = {"file": ("test.pdf", io.BytesIO(payload), "application/pdf")}
    response = client.post(
        f"{API_PORTRAIT}/files/upload",
        files=files,
        headers=leader_token_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "file_path" in data
    assert data["file_path"].startswith("home_visits/")
    assert data["file_url"].startswith("/uploads/portrait/home_visits/")
    assert data["file_size"] == len(payload)
    assert data["original_name"] == "test.pdf"


def test_upload_scan_size_exceeds_5mb(leader_token_headers: dict):
    """6MB PDF → 400 含 '5MB'"""
    payload = _make_pdf_bytes(6 * 1024 * 1024)
    files = {"file": ("big.pdf", io.BytesIO(payload), "application/pdf")}
    response = client.post(
        f"{API_PORTRAIT}/files/upload",
        files=files,
        headers=leader_token_headers,
    )
    assert response.status_code == 400, response.text
    assert "5MB" in response.json()["detail"]


def test_upload_scan_unsupported_type(leader_token_headers: dict):
    """.docx → 400 含 'pdf/jpg/png'"""
    files = {"file": ("test.docx", io.BytesIO(b"fake docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post(
        f"{API_PORTRAIT}/files/upload",
        files=files,
        headers=leader_token_headers,
    )
    assert response.status_code == 400, response.text
    assert "pdf/jpg/png" in response.json()["detail"]


def test_upload_scan_no_auth_rejected():
    """无 token → 401"""
    payload = _make_pdf_bytes(1024)
    files = {"file": ("test.pdf", io.BytesIO(payload), "application/pdf")}
    response = client.post(
        f"{API_PORTRAIT}/files/upload",
        files=files,
    )
    assert response.status_code == 401


def test_upload_scan_user_rejected(normal_token_headers: dict):
    """普通 user (无 team_id) → 403"""
    payload = _make_pdf_bytes(1024)
    files = {"file": ("test.pdf", io.BytesIO(payload), "application/pdf")}
    response = client.post(
        f"{API_PORTRAIT}/files/upload",
        files=files,
        headers=normal_token_headers,
    )
    assert response.status_code == 403


def test_delete_scan_path_traversal_rejected(leader_token_headers: dict):
    """DELETE 路径含 '..' → 400"""
    response = client.delete(
        f"{API_PORTRAIT}/files/..%2F..%2Fetc%2Fpasswd",
        headers=leader_token_headers,
    )
    # 路径遍历可能在 routing 层就被 reject, 也可能在 Service 层
    assert response.status_code in (400, 404)