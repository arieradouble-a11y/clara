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


def get_check_provider(name: str | None = None, **kwargs) -> LLMProvider:
    """Resolve the provider for the *faithfulness check*, kept separate from the
    simplifier so a model never grades its own rewrite.

    A model asked whether its own output is faithful tends to say yes; a second,
    independent model is a more honest judge. Resolution order: the explicit
    `name`, then CLARA_CHECK_PROVIDER, then the normal CLARA_PROVIDER default. So
    the check falls back to the same provider when no second one is configured —
    still useful, just not anti-self-grading.
    """
    name = name or os.environ.get("CLARA_CHECK_PROVIDER")
    return get_provider(name, **kwargs)


__all__ = [
    "LLMProvider",
    "MockProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "get_provider",
    "get_check_provider",
]
