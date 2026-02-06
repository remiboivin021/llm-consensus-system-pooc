from __future__ import annotations

from typing import Iterable, TypedDict

from src.contracts.response import ModelResponse, ScoreDetail, ScoreStats


class ScoreInput(TypedDict, total=False):
    model: str
    content: str | None
    latency_ms: int | None
    error: bool


def from_model_responses(responses: Iterable[ModelResponse]) -> list[ScoreInput]:
    items: list[ScoreInput] = []
    for response in responses:
        items.append(
            {
                "model": response.model,
                "content": response.content,
                "latency_ms": response.latency_ms,
                "error": response.error is not None,
            }
        )
    return items


def to_contract(details: list[ScoreDetail], stats: ScoreStats) -> tuple[list[ScoreDetail], ScoreStats]:
    return details, stats
