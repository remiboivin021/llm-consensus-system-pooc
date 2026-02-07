from __future__ import annotations

import json
from typing import Callable, Tuple

ValidationResult = Tuple[bool, str | None]
ValidatorFunc = Callable[[str], ValidationResult]


def json_validator(content: str) -> ValidationResult:
    try:
        json.loads(content)
        return True, None
    except Exception as exc:  # pragma: no cover - simple mapping
        return False, str(exc)


def resolve_validator(kind: str | None, explicit: ValidatorFunc | None) -> ValidatorFunc | None:
    if explicit:
        return explicit
    if not kind:
        return None
    if kind == "json":
        return json_validator
    return None
