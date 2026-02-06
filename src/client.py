from __future__ import annotations

from typing import Optional

from src.adapters.orchestration.orchestrator import OrchestrationError, Orchestrator
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult
from src.core.consensus.registry import DEFAULT_STRATEGY, get_strategy, list_strategies
from src.errors import LcsError, from_envelope


class LcsClient:
    """Public façade for running consensus without exposing internal details."""

    def __init__(self, default_strategy: str = DEFAULT_STRATEGY) -> None:
        self.default_strategy = default_strategy

    async def run(
        self, request: ConsensusRequest, strategy: Optional[str] = None
    ) -> ConsensusResult:
        strategy_name = strategy or request.strategy or self.default_strategy
        judge = get_strategy(strategy_name)
        orchestrator = Orchestrator(judge=judge)
        try:
            return await orchestrator.run(request, request.request_id, strategy_label=judge.method)
        except OrchestrationError as exc:
            raise from_envelope(exc.envelope)


async def consensus(request: ConsensusRequest, strategy: Optional[str] = None) -> ConsensusResult:
    client = LcsClient()
    return await client.run(request, strategy=strategy)


__all__ = ["LcsClient", "consensus", "list_strategies"]
