from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from src.contracts.response import ModelResponse, ScoreDetail


@dataclass
class Vote:
    model: str
    score: float


@dataclass
class JudgementResult:
    winner: str | None
    confidence: float
    method: str
    votes: list[Vote]
    rationale: str | None = None
    disagreements: list[str] | None = None


class Judge(Protocol):
    method: str

    def judge(
        self, responses: List[ModelResponse], scores: List[ScoreDetail] | None = None
    ) -> JudgementResult:
        ...
