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
    enable_auto_trading_scheduler: bool = False
    auto_trading_paper_cash_per_trade: float = 10000.0
    daily_collection_hour: int = 16
    daily_collection_minute: int = 10
    timezone: str = "Asia/Shanghai"
    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_use_tls: bool = True
    app_base_url: str = "http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
