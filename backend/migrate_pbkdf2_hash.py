"""
迁移脚本: legacy bcrypt hash → PBKDF2 hash (PRD §17.3)
=========================================================

背景: v2.0 安全基线回退, security.py 从 bcrypt 切换到 PBKDF2-HMAC-SHA256.
旧用户 (hashed_password 以 $2a$/$2b$/$2y$ 开头) 无法重算 (原密码不可得).

策略:
  - 检测所有 legacy 用户
  - 把 hashed_password 重置为 PBKDF2 哈希 (密码 = EHR 号, 数字 7 位, 与默认密码策略一致)
  - 标记 is_first_login = True (强制首次改密, PRD §3.2)

使用:
    python -m backend.migrate_pbkdf2_hash           # 实际迁移
    python -m backend.migrate_pbkdf2_hash --dry-run  # 仅统计，不改

环境: 必须能访问 app.core.config 中配置的数据库 (默认 SQLite).
"""
import argparse
import logging
from typing import Tuple

from app.db.session import SessionLocal
from app import models
from app.core.security import (
    get_password_hash,
    is_legacy_hash,
)
from app.portrait.models.user_metadata import PortraitUserMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def migrate(dry_run: bool = False) -> Tuple[int, int]:
    """执行迁移. 返回 (已迁移用户数, 已是 PBKDF2 格式用户数)."""
    db = SessionLocal()
    try:
        all_users = db.query(models.User).all()
        logger.info("扫描到 %d 个用户", len(all_users))

        migrated = 0
        already_ok = 0

        for user in all_users:
            if not is_legacy_hash(user.hashed_password):
                already_ok += 1
                continue

            # 跳过没有 EHR 的用户 (理论上不应该存在, 防御性)
            if not user.ehr_id or len(user.ehr_id) != 7 or not user.ehr_id.isdigit():
                logger.warning(
                    "用户 %s (id=%d) EHR 异常, 跳过", user.username, user.id
                )
                continue

            if dry_run:
                logger.info(
                    "[DRY-RUN] 将迁移: %s (ehr=%s, id=%d)",
                    user.username, user.ehr_id, user.id,
                )
                migrated += 1
                continue

            # 重置密码为 EHR 号 (PBKDF2 格式)
            new_hash = get_password_hash(user.ehr_id)
            user.hashed_password = new_hash
            user.last_password_change = None  # 触发首次改密提示

            # 标记 is_first_login = True (强制首次改密)
            meta = (
                db.query(PortraitUserMetadata)
                .filter(PortraitUserMetadata.user_id == user.id)
                .first()
            )
            if meta:
                meta.is_first_login = True
            else:
                db.add(PortraitUserMetadata(user_id=user.id, is_first_login=True))

            logger.info(
                "已迁移: %s (ehr=%s) -> 临时密码 = EHR号",
                user.username, user.ehr_id,
            )
            migrated += 1

        if not dry_run:
            db.commit()
            logger.info("✅ 已提交 %d 条迁移", migrated)
        else:
            db.rollback()
            logger.info("✅ [DRY-RUN] 完成, 未实际修改")

        return migrated, already_ok

    except Exception:
        db.rollback()
        logger.exception("迁移失败, 已回滚")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="bcrypt -> PBKDF2 迁移")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计, 不修改数据库",
    )
    args = parser.parse_args()
    migrated, already_ok = migrate(dry_run=args.dry_run)
    logger.info(
        "统计: 迁移 %d, 已就位 %d, 总 %d",
        migrated, already_ok, migrated + already_ok,
    )


if __name__ == "__main__":
    main()