"""Observability instrumentation - logs, metrics, traces."""
from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    consensus_duration_seconds,
    llm_call_duration_seconds,
    llm_calls_total,
    quality_score,
    quality_score_stats,
)

__all__ = [
    "get_logger",
    "consensus_duration_seconds",
    "llm_call_duration_seconds",
    "llm_calls_total",
    "quality_score",
    "quality_score_stats",
]