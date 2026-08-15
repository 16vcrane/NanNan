from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://nannan:nannan@localhost:5432/nannan"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    idempotency_lock_seconds: int = 60
    idempotency_result_seconds: int = 86400
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120
    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout_seconds: float = 30.0
    reflection_max_attempts: int = 3
    storage_endpoint: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_driver: str = "local"
    storage_local_path: str = "./storage/uploads"
    storage_region: str = "auto"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
