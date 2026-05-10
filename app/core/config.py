from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "enterprise-agentops-platform"
    app_env: str = "production"
    database_url: str = "postgresql+psycopg://agent_app:change_me@127.0.0.1:5432/enterprise_agents"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle_seconds: int = 1800
    database_echo: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    session_ttl_seconds: int = 24 * 60 * 60
    enable_external_search: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
