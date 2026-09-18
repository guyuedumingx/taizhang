"""
P1 阶段 1.5: 数字画像 users → taizhang users 数据迁移脚本

来源: digital_portrait/backend/digital_portrait.db (SQLite)
目标: taizhang/backend/taizhang.db (SQLite, dev) / Oracle (prod)

执行:
    cd D:\\code\\taizhang\\backend
    python migrate_portrait_p1.py            # 真迁移
    --dry-run                                # 只打印计划
    --source-path=<path>                     # 自定义源 DB

设计:
  ✅ 显式报告 created / skipped / errors 计数 (Rule 12)
  ✅ bcrypt 一次性重算全量, 强制所有用户首次登录改密
  ✅ ehr_no 7 位数字硬校验 (集成指南 §2 冲突 2)
  ✅ is_disabled=True → is_active=False 语义反转 (集成指南 §2 冲突 3)
  ✅ role 字段废弃, 全部走 Casbin (集成指南 §2 冲突 4)
  ✅ 失败行不中断, 跳过并记录到 errors 列表
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from typing import List, Tuple

# Windows GBK 默认编码不让打印 ❌, 强制 UTF-8 让错误明细可见 (Rule 12)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from passlib.context import CryptContext

# ---------- bcrypt 单点修复 (集成指南 §3 阶段 1.2) ----------
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_RESET_HASH_PLACEHOLDER = "__PORTRAIT_RESET__"


def beijing_now() -> datetime:
    """数字画像 / 台账统一用北京时间 (UTC+8) 无时区时间戳"""
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


def validate_ehr(ehr_no: str) -> bool:
    """集成指南 §2 冲突 2: EHR 必须是 7 位数字"""
    if not ehr_no:
        return False
    return len(ehr_no) == 7 and ehr_no.isdigit()


def map_role_to_casbin(role: str) -> str:
    """集成指南 §2 冲突 4: 数字画像 role 字段废弃, 改用 Casbin policy.csv"""
    # 这里只返回原始 role, 真正的 Casbin 角色分配在 policy.csv 配:
    #   p, <user_or_role>, portrait_resource, action
    return role or "user"


def migrate_users(source_path: str, dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """从 digital_portrait SQLite 读 users, 写入 taizhang.

    Returns: (created, skipped, errors)
    """
    if not os.path.exists(source_path):
        return 0, 0, [f"源数据库文件不存在: {source_path}"]

    src = sqlite3.connect(source_path)
    src.row_factory = sqlite3.Row
    try:
        rows = src.execute(
            """
            SELECT id, ehr_no, name, group_name, role,
                   password_hash, is_disabled, is_first_login,
                   is_superadmin, deleted_at, created_at, updated_at
            FROM users
            ORDER BY id
            """
        ).fetchall()
    finally:
        src.close()

    # 目标 DB 用 taizhang 的 SQLAlchemy session, 走标准路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.db.session import SessionLocal, engine, Base
    # 触发 taizhang + portrait 模型注册到 Base.metadata (User 必须先注册, 否则 FK 报错)
    import app.models  # noqa: F401
    import app.portrait.models  # noqa: F401

    if dry_run:
        Base.metadata.create_all(bind=engine)  # 仅建 portrait 表

    created, skipped = 0, 0
    errors: List[str] = []

    db = SessionLocal()
    try:
        from app.models.user import User
        from app.portrait.models.user_metadata import PortraitUserMetadata

        for r in rows:
            ehr_no = r["ehr_no"]
            name = r["name"]
            group_name = r["group_name"]
            role = r["role"]
            is_disabled = bool(r["is_disabled"])
            is_first_login = bool(r["is_first_login"])
            is_superadmin = bool(r["is_superadmin"])
            deleted_at_raw = r["deleted_at"]
            src_id = r["id"]

            # === 硬校验 ===
            if not validate_ehr(ehr_no):
                errors.append(f"id={src_id}: ehr_no='{ehr_no}' 不是 7 位数字, 跳过")
                skipped += 1
                continue

            # 检查目标库是否已存在 (按 ehr_id 唯一性)
            existing = db.query(User).filter(User.ehr_id == ehr_no).first()
            if existing:
                errors.append(f"id={src_id}: ehr_id={ehr_no} 已存在, 跳过")
                skipped += 1
                continue

            # === 一次性 bcrypt 重算 ===
            # 现有用户的 PBKDF2 hash 无法还原明文, 一律置为统一占位 hash,
            # is_first_login=True → 用户首次登录必须改密。
            new_hash = pwd_ctx.hash(DEFAULT_RESET_HASH_PLACEHOLDER)

            # 软删除映射: taizhang 没有 deleted_at, 我们用 PortraitUserMetadata 承载
            deleted_at = None
            if deleted_at_raw:
                try:
                    deleted_at = datetime.fromisoformat(str(deleted_at_raw).replace("Z", "+00:00"))
                    if deleted_at.tzinfo:
                        deleted_at = deleted_at.replace(tzinfo=None)
                except (ValueError, TypeError):
                    pass

            # === 语义反转: is_disabled=True → is_active=False ===
            new_is_active = not is_disabled

            if dry_run:
                print(
                    f"[DRY-RUN] 将创建: ehr_id={ehr_no}, name={name}, "
                    f"department={group_name}, is_active={new_is_active}, "
                    f"is_superuser={is_superadmin}, role_Casbin={map_role_to_casbin(role)}, "
                    f"is_first_login=True (强制改密)"
                )
                created += 1
                continue

            try:
                new_user = User(
                    username=ehr_no,             # taizhang 用 username, 复用 EHR
                    ehr_id=ehr_no,
                    hashed_password=new_hash,
                    name=name,
                    department=group_name,
                    is_active=new_is_active,
                    is_superuser=is_superadmin,
                    # team_id 留给人工绑定 (数字画像 group → 台账 teams 表)
                    team_id=None,
                )
                db.add(new_user)
                db.flush()  # 拿到 new_user.id

                # 写扩展表
                meta = PortraitUserMetadata(
                    user_id=new_user.id,
                    is_first_login=True,         # 一律强制改密
                    deleted_at=deleted_at,
                )
                db.add(meta)
                db.commit()
                created += 1
            except Exception as e:
                db.rollback()
                errors.append(f"id={src_id}, ehr_id={ehr_no}: {type(e).__name__}: {e}")
                skipped += 1
    finally:
        db.close()

    return created, skipped, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="P1 阶段 1.5: 数字画像 users → taizhang users")
    parser.add_argument(
        "--source-path",
        default=r"D:\code\digital_portrait\backend\digital_portrait.db",
        help="数字画像源 DB 文件",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印计划, 不实际写入",
    )
    args = parser.parse_args()

    print(f"=== P1 阶段 1.5: 数字画像 users → taizhang users 迁移 ===")
    print(f"源 DB:   {args.source_path}")
    print(f"目标 DB: taizhang 当前配置")
    print(f"模式:    {'DRY-RUN' if args.dry_run else 'LIVE'}\n")

    created, skipped, errors = migrate_users(args.source_path, dry_run=args.dry_run)

    print(f"\n=== 迁移完成 ===")
    print(f"  created: {created}")
    print(f"  skipped: {skipped}")
    print(f"  errors:  {len(errors)}")
    if errors:
        print(f"\n--- 错误明细 ---")
        for e in errors:
            print(f"  ❌ {e}")

    # Rule 12: 失败必须显性化 (退出码)
    if errors:
        print(f"\n⚠️  有 {len(errors)} 条记录跳过, 请人工处理后再回归")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())