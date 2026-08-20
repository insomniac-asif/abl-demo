"""Pluggable "thinking" backends for the demo agents.

By default the demo runs fully offline with a deterministic MockProvider, so a
reviewer can clone the repo and `python demo.py` with no keys, no GPU, and no
network. Set ABL_DEMO_PROVIDER to swap in a real LLM:

    ABL_DEMO_PROVIDER=mock        # default, scripted & offline
    ABL_DEMO_PROVIDER=anthropic   # needs ANTHROPIC_API_KEY + `pip install anthropic`
    ABL_DEMO_PROVIDER=ollama      # needs a local Ollama daemon (OLLAMA_MODEL)

The real providers are intentionally thin — this is a showcase of the *protocol*
(peer bus + consensus), not of any particular model.
"""

from __future__ import annotations

import os
from typing import Protocol


class Provider(Protocol):
    """Anything that can turn a system prompt + user prompt into text."""

    def complete(self, system: str, prompt: str) -> str: ...


class MockProvider:
    """Deterministic, offline provider.

    Returns scripted responses keyed by markers the agents put in their prompts.
    This keeps the demo reproducible and reviewable without external services.
    """

    def __init__(self, script: dict[str, str] | None = None) -> None:
        self._script = script or {}

    def complete(self, system: str, prompt: str) -> str:
        for marker, response in self._script.items():
            if marker in prompt:
                return response
        # Fall back to a generic, domain-flavored line drawn from the system role.
        role = system.splitlines()[0] if system else "agent"
        return f"[{role}] acknowledged: {prompt.strip()[:80]}"


class AnthropicProvider:
    """Thin wrapper over the Anthropic SDK (optional)."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # imported lazily so the dep is optional
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "ABL_DEMO_PROVIDER=anthropic needs the SDK: pip install anthropic"
            ) from exc

        try:
            api_key = os.environ["ANTHROPIC_API_KEY"]
        except KeyError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "ABL_DEMO_PROVIDER=anthropic needs ANTHROPIC_API_KEY to be set"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


class OllamaProvider:
    """Thin wrapper over a local Ollama daemon (optional, local-first)."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.environ.get("OLLAMA_MODEL", "llama3")

    def complete(self, system: str, prompt: str) -> str:
        import json
        import urllib.request

        body = json.dumps(
            {
                "model": self._model,
                "system": system,
                "prompt": prompt,
                "stream": False,
            }
        ).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read()).get("response", "")
        except OSError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "ABL_DEMO_PROVIDER=ollama could not reach the Ollama daemon at "
                f"http://localhost:11434 (model {self._model!r}). Is it running?"
            ) from exc


def provider_from_env(mock_script: dict[str, str] | None = None) -> Provider:
    """Select a provider based on ABL_DEMO_PROVIDER (defaults to mock)."""
    choice = os.environ.get("ABL_DEMO_PROVIDER", "mock").lower()
    if choice == "anthropic":
        return AnthropicProvider()
    if choice == "ollama":
        return OllamaProvider()
    return MockProvider(mock_script)
