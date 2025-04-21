from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_v1.api import api_router
from app.core.config import settings
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 配置日志
def setup_logging():
    # 创建日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取根目录的日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除现有的处理程序
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 添加控制台处理程序
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # 添加文件处理程序
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'backend.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # 配置第三方库的日志级别
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    logging.info("日志系统已初始化，日志文件路径: %s", log_file)

# 设置日志
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="台账管理系统API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    logging.info("访问根路径")
    return {"message": "台账管理系统API服务"}

@app.on_event("startup")
async def startup_event():
    logging.info("服务启动")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("服务关闭")

if __name__ == "__main__":
    import uvicorn
    logging.info("启动服务器...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True) 