import json
from functools import cached_property, lru_cache
from typing import Dict, Optional

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
    internal_api_key: Optional[str] = None
    api_key_header_name: str = "X-API-Key"
    enable_api_docs: bool = False
    expose_internal_traces: bool = False
    auth_tokens_json: str = "{}"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production or self.enable_api_docs

    @cached_property
    def auth_tokens(self) -> Dict[str, Dict[str, str]]:
        raw = self.auth_tokens_json.strip() or "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("AUTH_TOKENS_JSON must decode to an object")
        normalized: Dict[str, Dict[str, str]] = {}
        for token, claims in parsed.items():
            if not isinstance(claims, dict):
                raise ValueError("each auth token entry must be an object")
            employee_id = str(claims.get("employee_id") or "").strip()
            role = str(claims.get("role") or "").strip()
            if not employee_id or not role:
                raise ValueError("each auth token must include employee_id and role")
            normalized[str(token)] = {"employee_id": employee_id, "role": role}
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
