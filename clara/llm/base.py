"""Provider-agnostic LLM layer.

The engine never talks to a specific vendor directly — it talks to an
LLMProvider. This keeps the core independent, makes tests hermetic (MockProvider
runs offline), and lets privacy-sensitive documents stay on a local model
(Ollama) as a first-class option rather than an afterthought.

HTTP libraries are imported lazily inside each call so `import clara` works with
no network dependency installed and the offline MockProvider path stays clean.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2000, temperature: float = 0.2
    ) -> str:
        """Return the model's completion for `prompt` under `system` guidance."""


class MockProvider(LLMProvider):
    """Offline provider for tests and first-run demos.

    With no `response`, it echoes the user prompt unchanged. Because simplify()
    puts the instructions in the *system* message and the raw source text in the
    *prompt*, echoing the prompt returns the source verbatim — so the pipeline
    runs end-to-end and the faithfulness check reports OK. Pass an explicit
    `response` to simulate a model that drops or invents facts.
    """

    def __init__(self, response: str | None = None):
        self.response = response

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        return self.response if self.response is not None else prompt


class OpenAIProvider(LLMProvider):
    """OpenAI and any OpenAI-compatible endpoint (set OPENAI_BASE_URL)."""

    def __init__(self, api_key=None, model=None, base_url=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("CLARA_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        import httpx

        r = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API."""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or os.environ.get("CLARA_MODEL", "claude-sonnet-5")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        import httpx

        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


class OllamaProvider(LLMProvider):
    """Local models via Ollama — the privacy path. No API key, nothing leaves
    the machine, which matters for medical and legal documents."""

    def __init__(self, model=None, base_url=None):
        self.model = model or os.environ.get("CLARA_MODEL", "llama3.1")
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        import httpx

        r = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
