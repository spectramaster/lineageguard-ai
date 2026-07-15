from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LINEAGEGUARD_",
        extra="ignore",
    )

    app_name: str = "LineageGuard AI"
    environment: str = "development"
    datahub_gms_url: str = "http://localhost:8080"
    datahub_mcp_url: str = "stdio://mcp-server-datahub"
    datahub_token: str | None = None
    context_mode: str = "static"
    enable_datahub_writeback: bool = False
    github_token: str | None = None
    github_repository: str | None = None
    enable_github_pr: bool = False
    llm_provider: str = "deterministic"
    risk_auto_pr_threshold: int = Field(default=60, ge=0, le=100)
    risk_block_threshold: int = Field(default=80, ge=0, le=100)


@lru_cache
def get_settings() -> Settings:
    return Settings()
