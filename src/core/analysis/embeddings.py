from __future__ import annotations

import hashlib
import math
from typing import List


def _token_hash(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def embed_text(text: str, dims: int = 128) -> List[float]:
    if dims <= 0:
        return []
    vector = [0.0 for _ in range(dims)]
    tokens = text.split()
    if not tokens:
        return vector

    for token in tokens:
        idx = _token_hash(token) % dims
        vector[idx] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:  # pragma: no cover - unreachable with dims>0 and tokens present
        return vector
    return [value / norm for value in vector]
