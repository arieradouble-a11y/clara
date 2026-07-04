"""LLM provider registry and factory.

The default provider is `mock`, so `clara simplify` runs end-to-end offline out
of the box. Point it at a real model with the CLARA_PROVIDER env var (plus the
provider's key), e.g. CLARA_PROVIDER=anthropic ANTHROPIC_API_KEY=...
"""
from __future__ import annotations

import os

from .base import (
    AnthropicProvider,
    LLMProvider,
    MockProvider,
    OllamaProvider,
    OpenAIProvider,
)

_REGISTRY = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str | None = None, **kwargs) -> LLMProvider:
    name = (name or os.environ.get("CLARA_PROVIDER", "mock")).lower()
    if name not in _REGISTRY:
        raise ValueError(f"Unknown provider '{name}'. Options: {', '.join(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)


__all__ = [
    "LLMProvider",
    "MockProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "get_provider",
]
