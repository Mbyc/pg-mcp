import json
from typing import List, Optional, Dict, Any
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseConfig(BaseSettings):
    """单个数据库连接配置"""
    name: str
    dsn: str

class Settings(BaseSettings):
    """全局配置"""
    model_config = SettingsConfigDict(
        env_prefix="PG_MCP_", 
        env_file=".env", 
        extra="ignore",
        case_sensitive=False
    )
    
    # OpenAI 配置
    openai_api_key: SecretStr
    openai_model: str = "gpt-5-mini"
    openai_timeout_s: int = 30
    
    # 数据库配置 (支持通过环境变量传入 JSON 字符串)
    # 格式: PG_MCP_DATABASES='[{"name": "db1", "dsn": "postgresql://user:pass@host:port/db1"}]'
    databases: List[DatabaseConfig] = Field(default_factory=list)
    
    @field_validator("databases", mode="before")
    @classmethod
    def parse_databases(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
    # 默认数据库
    default_database: Optional[str] = None
    
    # 安全与性能
    statement_timeout_ms: int = 30000
    max_rows: int = 1000
    disallowed_functions: List[str] = [
        "pg_sleep", "pg_terminate_backend", "pg_cancel_backend",
        "pg_read_file", "pg_write_file", "pg_ls_dir"
    ]
    allow_multi_statement: bool = False
    
    # 缓存与 RAG
    schema_refresh_interval_s: int = 3600
    pool_idle_timeout_s: int = 300
    pool_max_size: int = 10
    pool_min_size: int = 1
    
    # 意义校验开关
    meaning_validation_enabled: bool = False
    meaning_validation_max_retries: int = 1

settings = Settings()
