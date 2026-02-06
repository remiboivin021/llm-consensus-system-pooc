from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable, Literal

import yaml
from pydantic import ValidationError

from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    policy_active_info,
    policy_reload_duration_seconds,
    policy_reload_total,
)
from src.policy.models import Policy, default_policy_path

logger = get_logger()

_BUILTIN_POLICY = {
    "policy_id": "default-v1",
    "description": "Built-in fallback policy",
    "gating_mode": "shadow",
    "breaker": {
        "enabled": True,
        "failure_threshold": 3,
        "open_ms": 15000,
        "failure_decay_ms": 60000,
    },
    "guardrails": {
        "request": {
            "prompt_min_chars": 1,
            "prompt_max_chars": 8000,
            "models": {
                "min_models": 1,
                "max_models": 5,
                "unique_required": True,
                "allowed_models": "*",
            },
        },
        "providers": {"require_at_least_n_success": 1, "max_failure_ratio": 0.75},
    },
    "consensus": {"judge": {"type": "score_preferred"}, "accept": {"min_confidence": 0.0}},
}


class PolicyReloadResult(Policy):
    """Policy reload result with status/telemetry fields."""

    status: Literal["success", "failure"]
    source: Literal["manual", "watcher"] = "manual"
    path: str | None = None
    error_reason: str | None = None
    reloaded_at_ms: int | None = None


def load_policy(path: str | None = None) -> Policy:
    """
    Load and validate the policy file.

    - Path resolution: explicit `path` takes precedence; otherwise use env `POLICY_FILE`,
      falling back to `policies/default.policy.yaml`.
    - Validation: Pydantic enforces schema; raises ValueError on invalid content.
    """
    candidate = path or os.environ.get("POLICY_FILE") or default_policy_path()
    policy_path = Path(candidate)
    if not policy_path.is_file():
        if path is None and os.environ.get("POLICY_FILE") is None:
            # fallback to built-in defaults when optional file is absent (e.g., mutation runs)
            return Policy.model_validate(_BUILTIN_POLICY)
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    with policy_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return Policy.model_validate(data)


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "file_not_found"
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, yaml.YAMLError):
        return "invalid_yaml"
    if isinstance(exc, (ValidationError, ValueError)):
        return "validation_error"
    return "unexpected_error"


def _emit_metrics(outcome: str, source: str, reason: str | None, policy: Policy | None, duration_ms: int) -> None:
    try:
        policy_reload_total.labels(outcome=outcome, source=source, reason=reason or "none").inc()
        policy_reload_duration_seconds.labels(source=source).observe(duration_ms / 1000)
    except Exception:
        logger.warning("policy_reload_metrics_error", outcome=outcome, source=source, reason=reason)

    if outcome == "success" and policy is not None:
        try:
            policy_active_info.labels(policy_id=policy.policy_id, gating_mode=policy.gating_mode).set(1)
        except Exception:
            logger.warning("policy_active_info_metrics_error", policy_id=getattr(policy, "policy_id", None))


class PolicyStore:
    """Thread-safe holder that supports manual reloads and optional watching."""

    def __init__(self, path: str | None = None, loader: Callable[[str | None], Policy] | None = None, policy: Policy | None = None) -> None:
        self._loader = loader or load_policy
        self._path = path
        self._lock = threading.Lock()
        self._last_mtime = self._path_mtime(path)
        self._policy = policy or self._loader(path)
        _emit_metrics("success", "init", None, self._policy, 0)
        self._watch_thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

    def current(self) -> Policy:
        return self._policy

    def reload(self, path: str | None = None, source: Literal["manual", "watcher"] = "manual") -> PolicyReloadResult:
        started = time.perf_counter()
        with self._lock:
            candidate = path or self._path or os.environ.get("POLICY_FILE") or default_policy_path()
            reason: str | None = None
            try:
                policy = self._loader(candidate)
                self._policy = policy
                self._path = candidate
                self._last_mtime = self._path_mtime(candidate)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                _emit_metrics("success", source, None, policy, elapsed_ms)
                logger.info(
                    "policy_reload_success",
                    path=str(candidate),
                    policy_id=policy.policy_id,
                    gating_mode=policy.gating_mode,
                    source=source,
                    elapsed_ms=elapsed_ms,
                )
                return PolicyReloadResult(
                    status="success",
                    source=source,
                    path=str(candidate),
                    error_reason=None,
                    reloaded_at_ms=elapsed_ms,
                    **policy.model_dump(),
                )
            except Exception as exc:  # pragma: no cover - classification covered separately
                reason = _classify_error(exc)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                _emit_metrics("failure", source, reason, None, elapsed_ms)
                logger.warning(
                    "policy_reload_failed",
                    path=str(candidate),
                    reason=reason,
                    error=str(exc),
                    source=source,
                    elapsed_ms=elapsed_ms,
                )
                return PolicyReloadResult(
                    status="failure",
                    source=source,
                    path=str(candidate),
                    error_reason=reason,
                    reloaded_at_ms=elapsed_ms,
                    **(self._policy.model_dump() if self._policy else {}),
                )

    def start_watcher(self, poll_interval_s: float = 2.0, debounce_s: float = 0.5) -> None:
        if self._path is None:
            raise ValueError("Cannot start watcher without a policy path")
        if self._watch_thread and self._watch_thread.is_alive():
            return

        self._stop_event = threading.Event()

        def _watch() -> None:
            last_seen = self._last_mtime
            while self._stop_event and not self._stop_event.is_set():
                time.sleep(poll_interval_s)
                mtime = self._path_mtime(self._path)
                if mtime is None or (last_seen is not None and mtime <= last_seen):
                    continue
                if time.time() - mtime < debounce_s:
                    continue
                result = self.reload(source="watcher")
                last_seen = mtime if result.status == "success" else mtime

        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()

    def stop_watcher(self) -> None:
        if self._stop_event is None:
            return
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=1.0)

    @staticmethod
    def _path_mtime(path: str | None) -> float | None:
        if path is None:
            return None
        candidate = Path(path)
        if not candidate.exists():
            return None
        return candidate.stat().st_mtime
