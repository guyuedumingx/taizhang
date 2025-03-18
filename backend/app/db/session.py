from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    poolclass=NullPool,  # 禁用连接池，确保每次请求使用新的连接
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 