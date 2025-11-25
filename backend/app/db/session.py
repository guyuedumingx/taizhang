from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 数据库连接池配置参数
# pool_size: 连接池中保持的连接数
#   - Oracle推荐: 20-50（取决于并发负载）
#   - SQLite推荐: 5-10
# max_overflow: 连接池可以扩展的最大连接数（超出pool_size的额外连接）
#   - Oracle推荐: 20-50（支持突发流量）
#   - SQLite推荐: 10-20
# pool_timeout: 获取连接的超时时间（秒），默认30
# pool_recycle: 连接回收时间（秒），防止连接长时间空闲后被数据库关闭
#   - Oracle推荐: 1800秒（30分钟），Oracle服务器可能会关闭空闲连接
#   - SQLite推荐: 3600秒（1小时）
# pool_pre_ping: 每次使用连接前ping一下，确保连接有效
#   - 对于Oracle数据库，建议保持True，因为网络不稳定或Oracle服务器可能关闭空闲连接
#   - 虽然会增加少量延迟，但可以避免"连接已关闭"错误

# Oracle数据库特定优化参数
# connect_args用于传递必要的Oracle特定参数（若有）
connect_args = {}

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,  # 连接前ping，确保连接有效（对Oracle很重要）
    pool_size=settings.DB_POOL_SIZE,  # 连接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,  # 最大溢出连接数
    pool_timeout=settings.DB_POOL_TIMEOUT,  # 获取连接超时时间
    pool_recycle=settings.DB_POOL_RECYCLE,  # 连接回收时间
    echo_pool=False,  # 是否打印连接池日志（调试时设为True）
    connect_args=connect_args if connect_args else {},  # Oracle特定连接参数
)

if settings.DATABASE_TYPE == "oracle":
    @event.listens_for(engine, "connect")
    def set_oracle_cursor_settings(dbapi_connection, connection_record):
        """在连接建立时设置Oracle游标参数，提升批量查询性能。"""
        cursor = None
        try:
            cursor = dbapi_connection.cursor()
            cursor.arraysize = settings.ORACLE_CURSOR_ARRAYSIZE
            if hasattr(cursor, "prefetchrows"):
                cursor.prefetchrows = settings.ORACLE_CURSOR_PREFETCHROWS
        except Exception as exc:
            print(f"[Oracle优化] 设置游标参数失败: {exc}")
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

# 连接池监控函数（用于调试和监控）
def get_pool_status():
    """
    获取连接池状态信息
    用于监控和调试连接池使用情况
    
    Returns:
        dict: 包含连接池详细状态信息的字典
    """
    try:
        pool = engine.pool
        pool_size = pool.size()
        max_overflow = pool._max_overflow if hasattr(pool, '_max_overflow') else 0
        
        checked_in = pool.checkedin()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        invalid = pool.invalid() if hasattr(pool, 'invalid') else 0
        current_connections = pool_size + overflow
        max_connections = pool_size + max_overflow
        
        # 计算使用率
        usage_percentage = (current_connections / max_connections * 100) if max_connections > 0 else 0
        
        # 获取配置信息
        config = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
            "database_type": settings.DATABASE_TYPE,
        }
        
        return {
            "config": config,
            "current_status": {
                "pool_size": pool_size,
                "checked_in": checked_in,  # 空闲连接数
                "checked_out": checked_out,  # 使用中的连接数
                "overflow": overflow,  # 溢出连接数
                "invalid": invalid,  # 无效连接数
                "current_connections": current_connections,  # 当前总连接数
                "max_connections": max_connections,  # 最大连接数
                "usage_percentage": round(usage_percentage, 2),  # 使用率百分比
            },
            "health": {
                "status": "healthy" if usage_percentage < 80 else "warning" if usage_percentage < 95 else "critical",
                "message": _get_pool_health_message(usage_percentage, overflow, checked_out, max_connections)
            }
        }
    except Exception as e:
        return {
            "error": f"无法获取连接池状态: {str(e)}",
            "status": "error"
        }

def _get_pool_health_message(usage_percentage: float, overflow: int, checked_out: int, max_connections: int) -> str:
    """生成连接池健康状态消息"""
    if usage_percentage >= 95:
        return f"连接池使用率过高 ({usage_percentage:.1f}%)，建议增加pool_size或max_overflow"
    elif usage_percentage >= 80:
        return f"连接池使用率较高 ({usage_percentage:.1f}%)，建议监控"
    elif overflow > 0:
        return f"当前有{overflow}个溢出连接，连接池使用正常但接近上限"
    elif checked_out == 0:
        return "连接池空闲，所有连接均可用"
    else:
        return f"连接池运行正常，{checked_out}/{max_connections}个连接在使用中"

def log_pool_status():
    """打印连接池状态（用于调试）"""
    status = get_pool_status()
    if "error" in status:
        print(f"[连接池状态] 错误: {status['error']}")
        return
    
    current = status["current_status"]
    health = status["health"]
    print(f"[连接池状态] "
          f"池大小: {current['pool_size']}, "
          f"使用中: {current['checked_out']}, "
          f"空闲: {current['checked_in']}, "
          f"溢出: {current['overflow']}, "
          f"当前总连接: {current['current_connections']}/{current['max_connections']} "
          f"({current['usage_percentage']}%), "
          f"健康状态: {health['status']}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 