from typing import Optional

from openai import OpenAI

from app.core.config import Settings, get_settings


class LLMClientFactory:
    """Centralizes model client creation so provider keys stay in env config."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def is_enabled(self) -> bool:
        return bool(self._api_key())

    def create(self) -> OpenAI:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("No LLM API key configured")
        kwargs = {"api_key": api_key}
        base_url = self._base_url()
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)

    def model_name(self) -> str:
        if self.settings.llm_provider == "dashscope":
            return self.settings.llm_model
        return self.settings.openai_model

    def _api_key(self) -> Optional[str]:
        if self.settings.llm_provider == "dashscope":
            return self.settings.dashscope_api_key
        return self.settings.openai_api_key

    def _base_url(self) -> Optional[str]:
        if self.settings.llm_provider == "dashscope":
            return self.settings.llm_base_url
        return None
