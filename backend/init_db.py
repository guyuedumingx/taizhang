import logging

from app.db.init_db import init_db
from app.db.session import SessionLocal, Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    db = SessionLocal()
    try:
        # 创建表
        Base.metadata.create_all(bind=engine)
        logger.info("创建数据库表")
        
        # 初始化数据
        init_db(db)
        logger.info("初始化数据库数据")
    finally:
        db.close()


def main() -> None:
    logger.info("创建初始数据")
    init()
    logger.info("初始数据创建完成")


if __name__ == "__main__":
    main() 