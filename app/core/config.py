from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Aquant"
    app_env: str = "dev"
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://aquant:Hsy%40841121@8.148.181.1:3306/a_quant?charset=utf8mb4"
    candle_database_url: str = "mysql+pymysql://aquant:Hsy%40841121@8.148.181.1:3306/a_candle?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    data_provider_mode: str = "real"
    admin_token: str = "dev-admin-token"
    enable_scheduler: bool = False
    daily_collection_hour: int = 16
    daily_collection_minute: int = 10
    timezone: str = "Asia/Shanghai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
