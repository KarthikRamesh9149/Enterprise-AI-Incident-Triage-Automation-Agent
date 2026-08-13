import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    local_demo_mode: bool = False
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    database_url: str = "sqlite:///./incident_triage.sqlite3"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str | None = None
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
    auto_seed: bool = False
    session_cookie_name: str = "incident_agent_session"

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def jwt_signing_key(self) -> str:
        if self.jwt_secret is None:  # guarded by validation; keeps the type explicit
            raise RuntimeError("JWT signing key is unavailable")
        return self.jwt_secret

    @property
    def secure_session_cookie(self) -> bool:
        return self.app_env.lower() not in {"local", "test"}

    @model_validator(mode="after")
    def validate_security_boundary(self) -> "Settings":
        env = self.app_env.lower()
        if self.local_demo_mode and env not in {"local", "test"}:
            raise ValueError("LOCAL_DEMO_MODE is only permitted in local or test environments")
        if self.auto_seed and not self.local_demo_mode:
            raise ValueError("AUTO_SEED requires explicit LOCAL_DEMO_MODE=true")
        if not self.jwt_secret:
            if not self.local_demo_mode:
                raise ValueError("JWT_SECRET is required unless LOCAL_DEMO_MODE=true")
            self.jwt_secret = secrets.token_urlsafe(48)
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if self.jwt_algorithm != "HS256":
            raise ValueError("Only JWT_ALGORITHM=HS256 is supported")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
