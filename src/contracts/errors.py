from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    type: Literal[
        "timeout",
        "http_error",
        "rate_limited",
        "invalid_response",
        "config_error",
        "internal",
        "provider_error",
    ]
    message: str
    retryable: bool = False
    status_code: int | None = None
