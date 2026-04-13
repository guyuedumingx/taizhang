import json
import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # CORS配置
    CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:5173"]

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "台账管理系统"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(BASE_DIR)
    # 数据库配置
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite 或 oracle
    
    # SQLite配置
    SQLITE_DATABASE_URI: str = f"sqlite:///{BASE_DIR}/../taizhang.db?check_same_thread=False"
    print(SQLITE_DATABASE_URI)
    
    # Oracle配置
    ORACLE_USER: Optional[str] = os.getenv("ORACLE_USER")
    ORACLE_PASSWORD: Optional[str] = os.getenv("ORACLE_PASSWORD")
    ORACLE_HOST: Optional[str] = os.getenv("ORACLE_HOST", "localhost")
    ORACLE_PORT: Optional[str] = os.getenv("ORACLE_PORT", "1521")
    ORACLE_SERVICE: Optional[str] = os.getenv("ORACLE_SERVICE")
    ORACLE_CURSOR_ARRAYSIZE: int = int(os.getenv("ORACLE_CURSOR_ARRAYSIZE", "100"))
    ORACLE_CURSOR_PREFETCHROWS: int = int(os.getenv("ORACLE_CURSOR_PREFETCHROWS", "100"))
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        生成数据库连接URI
        Oracle连接字符串使用service_name方式，性能优化参数通过connect_args传递（见session.py）
        """
        if self.DATABASE_TYPE == "oracle" and all([self.ORACLE_USER, self.ORACLE_PASSWORD, self.ORACLE_SERVICE]):
            # Oracle连接字符串
            # 注意：arraysize和fetchsize等性能参数在session.py中通过connect_args配置
            # 这样可以避免在URL中暴露敏感参数，并且提供更好的性能控制
            return f"oracle+cx_oracle://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_HOST}:{self.ORACLE_PORT}/?service_name={self.ORACLE_SERVICE}"
        return self.SQLITE_DATABASE_URI
    
    # Casbin配置
    CASBIN_MODEL_PATH: str = "app/core/rbac_model.conf"
    
    # 数据库连接池配置
    # Oracle数据库建议使用更大的连接池以提高性能
    # 默认值针对Oracle优化：pool_size=20, max_overflow=20
    # SQLite可以使用较小的连接池，可通过环境变量覆盖
    _default_pool_size = "20" if os.getenv("DATABASE_TYPE", "sqlite") == "oracle" else "5"
    _default_max_overflow = "20" if os.getenv("DATABASE_TYPE", "sqlite") == "oracle" else "10"
    _default_pool_recycle = "1800" if os.getenv("DATABASE_TYPE", "sqlite") == "oracle" else "3600"  # Oracle建议30分钟回收
    
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", _default_pool_size))  # 连接池大小，Oracle默认20，SQLite默认5
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", _default_max_overflow))  # 最大溢出连接数，Oracle默认20，SQLite默认10
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # 获取连接超时时间（秒），默认30
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", _default_pool_recycle))  # 连接回收时间（秒），Oracle默认1800（30分钟），SQLite默认3600（1小时）

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings() 