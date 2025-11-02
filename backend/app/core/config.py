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
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_TYPE == "oracle" and all([self.ORACLE_USER, self.ORACLE_PASSWORD, self.ORACLE_SERVICE]):
            return f"oracle+cx_oracle://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_HOST}:{self.ORACLE_PORT}/?service_name={self.ORACLE_SERVICE}"
        return self.SQLITE_DATABASE_URI
    
    # Casbin配置
    CASBIN_MODEL_PATH: str = "app/core/rbac_model.conf"
    
    # 数据库连接池配置
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))  # 连接池大小，默认5
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))  # 最大溢出连接数，默认10
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # 获取连接超时时间（秒），默认30
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 连接回收时间（秒），默认3600（1小时）
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings() 