from __future__ import annotations

from src.contracts.safety import PromptTruncationInfo


def truncate_middle(prompt: str, max_chars: int) -> tuple[str, PromptTruncationInfo]:
    """
    Deterministic middle-ellipsis truncation (ASCII '...').
    """
    info = PromptTruncationInfo(
        enabled=True,
        applied=False,
        original_chars=len(prompt),
        truncated_chars=len(prompt),
        removed_bytes=0,
        note=None,
    )
    if len(prompt) <= max_chars:
        return prompt, info

    ellipsis = "..."
    if max_chars <= len(ellipsis) + 1:
        truncated = prompt[:max_chars]
    else:
        head_len = (max_chars - len(ellipsis)) // 2
        tail_len = max_chars - len(ellipsis) - head_len
        truncated = prompt[:head_len] + ellipsis + prompt[-tail_len:]

    removed_bytes = len(prompt.encode("utf-8")) - len(truncated.encode("utf-8"))
    info.applied = True
    info.truncated_chars = len(truncated)
    info.removed_bytes = max(0, removed_bytes)
    info.note = "prompt auto-truncated with middle ellipsis"
    return truncated, info

