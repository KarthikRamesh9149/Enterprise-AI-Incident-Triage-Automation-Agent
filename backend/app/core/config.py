from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    database_url: str = "sqlite:///./incident_triage.sqlite3"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = Field(default="change-this-local-development-secret", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    llm_provider: str = "mock"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0
    max_output_tokens: int = 1200
    report_output_dir: str = "./reports"
    rate_limit_per_minute: int = 60
    tool_timeout_ms: int = 5000
    mock_provider_seed: str = "enterprise-incident-demo"
    auto_seed: bool = True

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
