import json
from functools import cached_property, lru_cache
from typing import Dict, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LOCAL_DATABASE_URL = "sqlite:///./data/app.db"
PRODUCTION_DATABASE_URL = "postgresql+psycopg://agent_app:change_me@127.0.0.1:5432/enterprise_agents"


class Settings(BaseSettings):
    app_name: str = "enterprise-agentops-platform"
    app_env: str = "local"
    database_url: str = LOCAL_DATABASE_URL
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle_seconds: int = 1800
    database_echo: bool = False
    llm_provider: str = "none"
    llm_base_url: Optional[str] = None
    llm_model: str = "qwen-plus"
    dashscope_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    session_ttl_seconds: int = 24 * 60 * 60
    enable_external_search: bool = False
    auto_init_local_db: bool = True
    vector_store: str = "milvus_lite"
    milvus_uri: str = "http://127.0.0.1:19530"
    milvus_token: Optional[str] = None
    milvus_lite_uri: str = "./data/milvus_lite.db"
    embedding_dim: int = 128
    internal_api_key: Optional[str] = None
    public_channel_token: Optional[str] = None
    public_channel_header_name: str = "X-Channel-Token"
    api_key_header_name: str = "X-API-Key"
    enable_api_docs: bool = False
    expose_internal_traces: bool = False
    auth_tokens_json: str = "{}"
    log_level: str = "INFO"
    usage_guard_enabled: bool = True
    usage_minute_request_limit: int = 12
    usage_hour_request_limit: int = 120
    usage_day_token_limit: int = 20000
    usage_single_input_token_limit: int = 2000
    usage_duplicate_window_seconds: int = 60
    usage_duplicate_limit: int = 3
    thread_lock_ttl_seconds: int = 120
    thread_history_limit: int = 12
    reflection_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def normalize_environment_defaults(self):
        if self.is_production:
            if self.database_url == LOCAL_DATABASE_URL:
                self.database_url = PRODUCTION_DATABASE_URL
            if self.vector_store == "milvus_lite":
                self.vector_store = "milvus"
        return self

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
