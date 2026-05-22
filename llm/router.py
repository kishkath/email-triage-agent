import logging
from typing import Optional

from pydantic import BaseModel

from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

log = logging.getLogger(__name__)


class RouterExhaustedException(Exception):
    pass


_PROVIDER_REGISTRY = {
    "GEMINI": GeminiProvider,
    "OPENAI": OpenAIProvider,
}


class LLMRouter:
    def __init__(self, primary: str, fallback: str):
        self.primary_name = primary
        self.fallback_name = fallback
        self.last_provider_used: Optional[str] = None
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, name: str) -> LLMProvider:
        if name not in self._providers:
            cls = _PROVIDER_REGISTRY.get(name)
            if cls is None:
                raise ValueError(f"Unknown provider: {name}")
            self._providers[name] = cls()
        return self._providers[name]

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Optional[type[BaseModel]] = None,
    ) -> str:
        errors = []
        for name in (self.primary_name, self.fallback_name):
            try:
                log.info("Trying provider: %s", name)
                provider = self._get_provider(name)
                text = provider.complete(system_prompt, user_message, response_schema)
                self.last_provider_used = name
                return text
            except Exception as e:  # noqa: BLE001
                log.warning("Provider %s failed: %s", name, e)
                errors.append(f"{name}: {e}")
        raise RouterExhaustedException("All providers failed: " + " | ".join(errors))
