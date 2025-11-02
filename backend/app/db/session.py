from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 数据库连接池配置参数
# pool_size: 连接池中保持的连接数，默认5
# max_overflow: 连接池可以扩展的最大连接数（超出pool_size的额外连接），默认10
# pool_timeout: 获取连接的超时时间（秒），默认30
# pool_recycle: 连接回收时间（秒），防止连接长时间空闲后被数据库关闭，默认3600
# pool_pre_ping: 每次使用连接前ping一下，确保连接有效

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,  # 连接前ping，确保连接有效
    pool_size=settings.DB_POOL_SIZE,  # 连接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,  # 最大溢出连接数
    pool_timeout=settings.DB_POOL_TIMEOUT,  # 获取连接超时时间
    pool_recycle=settings.DB_POOL_RECYCLE,  # 连接回收时间
    echo_pool=False,  # 是否打印连接池日志（调试时设为True）
)

# 连接池监控函数（可选，用于调试和监控）
def get_pool_status():
    """
    获取连接池状态信息
    用于监控和调试连接池使用情况
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
        "max_connections": pool.size() + pool._max_overflow,
        "current_connections": pool.size() + pool.overflow(),
    }

def log_pool_status():
    """打印连接池状态（用于调试）"""
    status = get_pool_status()
    print(f"[连接池状态] 池大小: {status['pool_size']}, "
          f"使用中: {status['checked_out']}, "
          f"空闲: {status['checked_in']}, "
          f"溢出: {status['overflow']}, "
          f"当前总连接: {status['current_connections']}/{status['max_connections']}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 