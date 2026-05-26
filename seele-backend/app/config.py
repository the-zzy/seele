"""
应用配置模块
"""

from typing import Optional
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 部署环境: dev | prod
    deploy_env: str = "dev"

    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "seele"

    # 应用配置
    app_host: str = "0.0.0.0"
    app_port: int = 9000

    # 东方财富API配置
    eastmoney_base_url: str = "https://push2.eastmoney.com"

    # Moonshot AI (Kimi) 配置
    moonshot_api_key: str = ""
    moonshot_model: str = "kimi-k2.6"

    # 认证配置
    secret_key: str = ""
    admin_password: str = "seele"

    # 以下为可覆盖参数，None 表示使用 deploy_env 自动推导
    db_pool_size: Optional[int] = None
    db_max_overflow: Optional[int] = None
    uvicorn_reload: Optional[bool] = None
    uvicorn_workers: Optional[int] = None
    sync_max_workers: Optional[int] = None

    @model_validator(mode="after")
    def apply_env_defaults(self):
        defaults = {
            "dev": {
                "db_pool_size": 20,
                "db_max_overflow": 10,
                "uvicorn_reload": True,
                "uvicorn_workers": 1,
                "sync_max_workers": 10,
            },
            "prod": {
                "db_pool_size": 5,
                "db_max_overflow": 5,
                "uvicorn_reload": False,
                "uvicorn_workers": 1,
                "sync_max_workers": 2,
            }
        }

        env_defaults = defaults.get(self.deploy_env, defaults["dev"])
        for key, value in env_defaults.items():
            if getattr(self, key) is None:
                setattr(self, key, value)

        if not self.secret_key:
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
        return self

    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()