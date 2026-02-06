from __future__ import annotations

from typing import Protocol

from src.adapters.orchestration.models import ProviderResult


class ProviderAdapter(Protocol):
    """Minimal provider contract used by the orchestrator."""

    name: str

    def supports(self, model: str) -> bool:
        """Return True if the provider can serve this model name."""

    async def call(
        self,
        prompt: str,
        model: str,
        request_id: str,
        system_preamble: str | None = None,
        provider_timeout_ms: int | None = None,
    ) -> ProviderResult:
        """Execute the provider call and return a ProviderResult."""
