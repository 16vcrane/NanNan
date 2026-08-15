import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_missing_secrets_and_https() -> None:
    with pytest.raises(ValidationError, match="production configuration invalid"):
        Settings(app_env="production")


def test_complete_production_configuration_is_accepted() -> None:
    settings = Settings(
        app_env="production",
        public_base_url="https://api.example.com",
        force_https=True,
        allowed_hosts="api.example.com",
        wechat_app_id="app-id",
        wechat_app_secret="app-secret",
        jwt_secret="x" * 32,
        llm_provider="openai_compatible",
        llm_model="model",
        llm_api_key="model-secret",
        storage_driver="s3",
        storage_endpoint="https://storage.example.com",
        storage_bucket="private-bucket",
        storage_access_key="storage-key",
        storage_secret_key="storage-secret",
    )

    assert settings.allowed_host_list == ["api.example.com"]
