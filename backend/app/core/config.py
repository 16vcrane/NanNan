from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    public_base_url: str = ""
    force_https: bool = False
    allowed_hosts: str = "localhost,127.0.0.1,testserver,test"
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

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self
        missing = []
        required = {
            "WECHAT_APP_ID": self.wechat_app_id,
            "WECHAT_APP_SECRET": self.wechat_app_secret,
            "JWT_SECRET": self.jwt_secret if len(self.jwt_secret) >= 32 else "",
            "LLM_PROVIDER": self.llm_provider,
            "LLM_MODEL": self.llm_model,
            "LLM_API_KEY": self.llm_api_key,
            "PUBLIC_BASE_URL": self.public_base_url,
        }
        if self.storage_driver == "s3":
            required.update(
                {
                    "STORAGE_ENDPOINT": self.storage_endpoint,
                    "STORAGE_BUCKET": self.storage_bucket,
                    "STORAGE_ACCESS_KEY": self.storage_access_key,
                    "STORAGE_SECRET_KEY": self.storage_secret_key,
                }
            )
        else:
            missing.append("STORAGE_DRIVER=s3")
        missing.extend(name for name, value in required.items() if not value)
        if self.public_base_url and urlparse(self.public_base_url).scheme != "https":
            missing.append("PUBLIC_BASE_URL must use https")
        if not self.force_https:
            missing.append("FORCE_HTTPS=true")
        if not self.allowed_host_list:
            missing.append("ALLOWED_HOSTS")
        if missing:
            raise ValueError("production configuration invalid: " + ", ".join(missing))
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
