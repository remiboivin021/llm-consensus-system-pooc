from __future__ import annotations

from typing import Optional
from uuid import uuid4

from src.adapters.orchestration.orchestrator import OrchestrationError, Orchestrator
from src.adapters.orchestration.models import fetch_provider_result
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult
from src.contracts.self_consistency import SelfConsistencyConfig, SelfConsistencyResult
from src.core.consensus.registry import DEFAULT_STRATEGY, get_strategy, list_strategies
from src.core.self_consistency import run_self_consistency as run_self_consistency_core
from src.config import get_settings
from src.errors import LcsError, from_envelope


class LcsClient:
    """Public façade for running consensus without exposing internal details."""

    def __init__(
        self,
        default_strategy: str = DEFAULT_STRATEGY,
        run_event_callback=None,
        callback_timeout_ms: int | None = 250,
        calibrator=None,
        output_validator=None,
    ) -> None:
        self.default_strategy = default_strategy
        self.run_event_callback = run_event_callback
        self.callback_timeout_ms = callback_timeout_ms
        self.calibrator = calibrator
        self.output_validator = output_validator

    async def run(
        self, request: ConsensusRequest, strategy: Optional[str] = None
    ) -> ConsensusResult:
        strategy_name = strategy or request.strategy or self.default_strategy
        judge = get_strategy(strategy_name)
        try:
            orchestrator = Orchestrator(
                judge=judge,
                run_event_callback=self.run_event_callback,
                callback_timeout_ms=self.callback_timeout_ms,
                calibrator=self.calibrator,
                output_validator=self.output_validator,
            )
        except TypeError:
            # Backward compatibility for patched/dummy orchestrators in tests
            orchestrator = Orchestrator(judge=judge)
        try:
            return await orchestrator.run(request, request.request_id, strategy_label=judge.method)
        except OrchestrationError as exc:
            raise from_envelope(exc.envelope)

    async def run_self_consistency(
        self,
        *,
        prompt: str,
        model: str,
        config: SelfConsistencyConfig | None = None,
        request_id: str | None = None,
    ) -> SelfConsistencyResult:
        cfg = config or SelfConsistencyConfig()
        settings = get_settings()
        if cfg.per_sample_timeout_ms is None:
            cfg = cfg.model_copy(update={"per_sample_timeout_ms": settings.provider_timeout_ms})
        req_id = request_id or str(uuid4())

        async def fetch(prompt_val, model_val, request_id_val, normalize_output, include_scores, provider_timeout_ms):
            timeout_ms = provider_timeout_ms or cfg.per_sample_timeout_ms
            return await fetch_provider_result(
                prompt_val,
                model_val,
                request_id_val,
                normalize_output,
                include_scores,
                timeout_ms,
            )

        return await run_self_consistency_core(
            prompt=prompt,
            model=model,
            request_id=req_id,
            fetch_fn=fetch,
            config=cfg,
        )


async def consensus(request: ConsensusRequest, strategy: Optional[str] = None) -> ConsensusResult:
    client = LcsClient()
    return await client.run(request, strategy=strategy)


__all__ = ["LcsClient", "consensus", "list_strategies"]
