"""
Centralized application configuration.

All environment-dependent values are read once here via pydantic-settings,
so the rest of the codebase never touches `os.environ` directly.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Database
    database_url: str = "postgresql+asyncpg://eap:eap_dev_password@localhost:5432/eap"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # LLM providers
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"

    # MCP servers
    mcp_postgres_url: str = "http://localhost:9101/sse"
    mcp_gmail_url: str = "http://localhost:9102/sse"
    mcp_drive_url: str = "http://localhost:9103/sse"


@lru_cache
def get_settings() -> Settings:
    return Settings()
