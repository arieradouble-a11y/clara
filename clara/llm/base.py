"""Provider-agnostic LLM layer.

The engine never talks to a specific vendor directly — it talks to an
LLMProvider. This keeps the core independent, makes tests hermetic (MockProvider
runs offline), and lets privacy-sensitive documents stay on a local model
(Ollama) as a first-class option rather than an afterthought.

Two entry points: `complete(system, prompt)` is the single-turn call the
simplify/verify pipeline uses; `chat(messages)` takes an OpenAI-style message
list for multi-turn conversations (the accessibility proxy forwards whole
dialogues). Vendor providers implement chat() natively and derive complete()
from it; the base class gives custom single-turn providers a flattening
fallback so they keep working behind the proxy.

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

    def chat(self, messages: list[dict], *, max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Multi-turn completion over an OpenAI-style message list.

        Vendor providers override this with their native chat API. This default
        flattens the conversation into complete() so a custom single-turn
        provider still works behind the proxy — degraded, not broken."""
        system = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        turns = [m for m in messages if m.get("role") != "system"]
        if len(turns) <= 1:
            prompt = str(turns[0].get("content", "")) if turns else ""
        else:
            prompt = "\n\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in turns)
        return self.complete(system, prompt, max_tokens=max_tokens, temperature=temperature)


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

    def chat(self, messages, *, max_tokens=2000, temperature=0.2):
        if self.response is not None:
            return self.response
        users = [m for m in messages if m.get("role") == "user"]
        return str(users[-1].get("content", "")) if users else ""


class OpenAIProvider(LLMProvider):
    """OpenAI and any OpenAI-compatible endpoint (set OPENAI_BASE_URL)."""

    def __init__(self, api_key=None, model=None, base_url=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("CLARA_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def chat(self, messages, *, max_tokens=2000, temperature=0.2):
        import httpx

        r = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": messages,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        return self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens, temperature=temperature,
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API."""

    def __init__(self, api_key=None, model=None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.api_key: str = key
        self.model = model or os.environ.get("CLARA_MODEL", "claude-sonnet-5")

    def chat(self, messages, *, max_tokens=2000, temperature=0.2):
        import httpx

        # Anthropic takes the system prompt as a separate field, not a message.
        system = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        body: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [m for m in messages if m.get("role") != "system"],
        }
        if system:
            body["system"] = system
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            json=body,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        return self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens, temperature=temperature,
        )


class OllamaProvider(LLMProvider):
    """Local models via Ollama — the privacy path. No API key, nothing leaves
    the machine, which matters for medical and legal documents."""

    def __init__(self, model=None, base_url=None):
        self.model = model or os.environ.get("CLARA_MODEL", "llama3.1")
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def chat(self, messages, *, max_tokens=2000, temperature=0.2):
        import httpx

        r = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "messages": messages,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        return self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens, temperature=temperature,
        )
