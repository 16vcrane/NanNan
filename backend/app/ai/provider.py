import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings


class LLMProviderError(Exception):
    pass


@dataclass(frozen=True)
class LLMResult:
    content: str
    model_name: str
    token_usage: int | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> LLMResult:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        if not settings.llm_api_key or not settings.llm_model:
            raise LLMProviderError("LLM is not configured")
        self.settings = settings
        self.client = client

    async def generate(self, prompt: str) -> LLMResult:
        base_url = (self.settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
        }
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds)
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {}).get("total_tokens")
            if not isinstance(content, str):
                raise ValueError("model content is not text")
            return LLMResult(
                content=content,
                model_name=body.get("model") or self.settings.llm_model,
                token_usage=usage if isinstance(usage, int) else None,
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderError("LLM request failed") from exc
        finally:
            if owns_client:
                await client.aclose()


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider(settings)
    raise LLMProviderError(f"unsupported LLM provider: {provider or 'empty'}")
