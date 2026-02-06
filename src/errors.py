from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LcsError(Exception):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


def from_envelope(envelope) -> "LcsError":  # pragma: no mutate
    """Convert existing ErrorEnvelope objects into LcsError."""
    etype = getattr(envelope, "type", "") or ""
    message = getattr(envelope, "message", "")
    has_retryable = hasattr(envelope, "retryable")
    retryable_raw = getattr(envelope, "retryable") if has_retryable else False
    retryable = bool(retryable_raw)
    status = getattr(envelope, "status_code", None)

    if etype == "timeout":
        code = "timeout"
    elif etype in {"http_error", "rate_limited", "invalid_response", "provider_error"}:
        code = "provider_error"
    elif etype == "config_error":
        code = "config_error"
    elif etype == "internal":
        code = "internal_error"
    else:
        code = "internal_error"

    details = {"status_code": status} if status is not None else None

    return LcsError(code=code, message=message, retryable=retryable, details=details)
