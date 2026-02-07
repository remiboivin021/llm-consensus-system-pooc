from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from src.policy.models import PiiPrefilter

# Lightweight, deterministic PII patterns; intentionally conservative.
_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\\+?\\d[\\d\\s().-]{6,}\\d"),
    "ipv4": re.compile(r"\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b"),
    "ipv6": re.compile(r"\\b[0-9a-fA-F:]{2,}\\:[0-9a-fA-F:]{2,}\\b"),
}


@dataclass
class RedactionEntry:
    type: str
    original: str
    mask: str
    start: int
    end: int


@dataclass
class RedactionResult:
    masked_prompt: str
    entries: List[RedactionEntry]
    counts: Dict[str, int]
    applied: bool
    truncated: bool = False


class RedactionConfigError(ValueError):
    pass


def _validate_rules(rules: List[str]) -> None:
    unknown = [r for r in rules if r not in _PATTERNS]
    if unknown:
        raise RedactionConfigError(f"Unknown PII rules: {','.join(unknown)}")


def redact_prompt(prompt: str, config: PiiPrefilter) -> RedactionResult:
    if not config.enabled:
        return RedactionResult(prompt, [], {}, applied=False)

    rules = config.rules or []
    _validate_rules(rules)

    matches: List[tuple[int, int, str, str]] = []
    for rule in rules:
        pattern = _PATTERNS[rule]
        for m in pattern.finditer(prompt):
            matches.append((m.start(), m.end(), rule, m.group(0)))

    matches.sort(key=lambda item: item[0])

    pieces: List[str] = []
    entries: List[RedactionEntry] = []
    counts: Dict[str, int] = {}
    idx = 0
    truncated = False

    for start, end, rule, text in matches:
        if start < idx:
            # overlap; skip to keep deterministic non-overlap behavior
            continue
        pieces.append(prompt[idx:start])
        counts[rule] = counts.get(rule, 0) + 1
        mask = f"<PII:{rule}:{counts[rule]}>"
        pieces.append(mask)
        if len(entries) < config.map_limit:
            entries.append(RedactionEntry(rule, text, mask, start, end))
        else:
            truncated = True
        idx = end
    pieces.append(prompt[idx:])

    masked = "".join(pieces)
    applied = bool(entries) or truncated
    return RedactionResult(masked, entries, counts, applied=applied, truncated=truncated)
