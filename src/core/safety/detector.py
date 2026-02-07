from __future__ import annotations

import re
import time
from typing import Callable

from src.contracts.safety import PromptSafetyConfig, PromptSafetyDecision

# Simple default keyword detector; deterministic and cheap.
DEFAULT_PATTERNS = [
    r"system_prompt",
    r"ignore previous",
    r"disregard above",
    r"override instructions",
    r"jailbreak",
    r"sudo ",
]


def default_detector(prompt: str, config: PromptSafetyConfig) -> PromptSafetyDecision:
    start = time.perf_counter()
    normalized = prompt.lower()
    for allowed in config.allowlist:
        if normalized == allowed.lower():
            return PromptSafetyDecision(action="allow", reason="allowlist")

    matched = False
    for pattern in DEFAULT_PATTERNS:
        if re.search(pattern, normalized):
            matched = True
            break

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    if matched:
        return PromptSafetyDecision(action="block" if config.mode == "block" else "warn", reason="keyword_match", details={"ms": elapsed_ms})
    return PromptSafetyDecision(action="allow", reason="clean", details={"ms": elapsed_ms})


DetectorFn = Callable[[str, PromptSafetyConfig], PromptSafetyDecision]


def run_prompt_safety(prompt: str, config: PromptSafetyConfig, detector: DetectorFn | None = None) -> PromptSafetyDecision:
    detector_fn = detector or default_detector
    start = time.perf_counter()
    try:
        decision = detector_fn(prompt, config)
    except Exception as exc:  # pragma: no cover - defensive
        return PromptSafetyDecision(action="warn", reason="detector_error", details={"error": str(exc)})
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    if elapsed_ms > config.max_eval_ms and decision.action == "allow":
        return PromptSafetyDecision(action="warn", reason="detector_timeout", details={"ms": elapsed_ms})
    return decision

