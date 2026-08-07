"""AI model provider abstraction (Doc 12 §12.2)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIModelProvider(Protocol):
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        model_config: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]: ...


class UnavailableAIProvider:
    """Default provider when FL-DEC-015 is unresolved — always fails fast."""

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        model_config: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "AI provider not configured (FL-DEC-015 unresolved); use deterministic fallback"
        )


def get_ai_provider() -> AIModelProvider:
    # Live Gemini/OpenAI wiring deferred until FL-DEC-015 (Doc 11 §26.2).
    return UnavailableAIProvider()
