from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable

import yaml
from pydantic import ValidationError

from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    policy_active_info,
    policy_reload_duration_seconds,
    policy_reload_total,
)
from src.policy.models import (
    Policy,
    PolicyMeta,
    PolicyReloadRequest,
    PolicyReloadResult,
    default_policy_path,
)

logger = get_logger()

_BUILTIN_POLICY = {
    "policy_id": "default-v1",
    "description": "Built-in fallback policy",
    "gating_mode": "shadow",
    "preambles": {"allow": "*"},
    "prefilter": {"pii": {"enabled": False, "rules": ["email", "phone", "ipv4"], "map_limit": 500}},
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
        return "missing_file"
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, yaml.YAMLError):
        return "invalid_yaml"
    if isinstance(exc, (ValidationError, ValueError)):
        return "invalid_schema"
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

    def __init__(
        self,
        path: str | None = None,
        loader: Callable[[str | None], Policy] | None = None,
        policy: Policy | None = None,
    ) -> None:
        self._loader = loader or load_policy
        self._path = path
        self._lock = threading.RLock()
        self._policy = policy or self._call_loader(path)
        mtime = self._path_mtime(path)
        self._meta = PolicyMeta(path=path, mtime=mtime, content_hash=None, loaded_at=self._now(), source="startup")
        self._initial_reload_done = False
        _emit_metrics("success", "startup", None, self._policy, 0)
        self._watch_thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

    @staticmethod
    def _now():
        import datetime as _dt

        return _dt.datetime.utcnow()

    def current(self) -> Policy:
        with self._lock:
            return self._policy

    def meta(self) -> PolicyMeta:
        with self._lock:
            return self._meta

    def reload(self, req: PolicyReloadRequest | None = None) -> PolicyReloadResult:
        req = req or PolicyReloadRequest(path=self._path, source="manual")
        started = time.perf_counter()
        candidate = req.path or self._path or os.environ.get("POLICY_FILE") or default_policy_path()
        path = Path(candidate)
        with self._lock:
            mtime = self._path_mtime(str(path))
            if mtime is None:
                return self._reject(req, str(path), "missing_file", ["file_not_found"], started)

            if (
                self._initial_reload_done
                and not req.force
                and self._meta.mtime is not None
                and mtime is not None
                and mtime <= self._meta.mtime
            ):
                duration_ms = int((time.perf_counter() - started) * 1000)
                _emit_metrics("unchanged", req.source, "unchanged", self._policy, duration_ms)
                logger.info(
                    "policy_reload_unchanged",
                    path=str(path),
                    source=req.source,
                    mtime=mtime,
                )
                self._initial_reload_done = True
                return PolicyReloadResult(
                    status="unchanged",
                    policy_id=self._policy.policy_id,
                    version=self._policy.version,
                    path=str(path),
                    reason="unchanged",
                    validation_errors=None,
                    loaded_at=self._meta.loaded_at,
                    previous_policy_id=self._policy.policy_id,
                )

            try:
                policy = self._call_loader(str(path))
            except Exception as exc:
                errors = []
                if isinstance(exc, ValidationError):
                    errors = [str(e) for e in exc.errors()]
                elif isinstance(exc, yaml.YAMLError):
                    errors = [str(exc)]
                reason = _classify_error(exc)
                return self._reject(req, str(path), reason, errors or [str(exc)], started)

            self._policy = policy
            self._path = str(path)
            self._meta = PolicyMeta(path=str(path), mtime=mtime, content_hash=None, loaded_at=self._now(), source=req.source)
            duration_ms = int((time.perf_counter() - started) * 1000)
            _emit_metrics("success", req.source, "accepted", policy, duration_ms)
            logger.info(
                "policy_reload_success",
                path=str(path),
                source=req.source,
                policy_id=policy.policy_id,
                version=policy.version,
                mtime=mtime,
                duration_ms=duration_ms,
            )
            self._initial_reload_done = True
            return PolicyReloadResult(
                status="accepted",
                policy_id=policy.policy_id,
                version=policy.version,
                path=str(path),
                reason=None,
                validation_errors=None,
                loaded_at=self._meta.loaded_at,
                previous_policy_id=None,
            )

    def _reject(
        self,
        req: PolicyReloadRequest,
        path: str,
        reason: str,
        errors: list[str],
        started: float,
    ) -> PolicyReloadResult:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _emit_metrics("failure", req.source, reason, None, duration_ms)
        logger.warning(
            "policy_reload_failed",
            path=str(path),
            source=req.source,
            reason=reason,
            errors=errors,
            duration_ms=duration_ms,
        )
        return PolicyReloadResult(
            status="rejected",
            policy_id=getattr(self._policy, "policy_id", None),
            version=getattr(self._policy, "version", None),
            path=str(path),
            reason=reason,
            validation_errors=errors,
            loaded_at=self._meta.loaded_at if hasattr(self, "_meta") else self._now(),
            previous_policy_id=getattr(self._policy, "policy_id", None),
        )
        self._initial_reload_done = True

    def start_watcher(self, poll_interval_s: float = 2.0, debounce_s: float = 0.5) -> None:
        if self._path is None:
            raise ValueError("Cannot start watcher without a policy path")
        if self._watch_thread and self._watch_thread.is_alive():
            return

        self._stop_event = threading.Event()

        def _watch() -> None:
            last_seen = self._meta.mtime
            while self._stop_event and not self._stop_event.is_set():
                time.sleep(poll_interval_s)
                mtime = self._path_mtime(self._path)
                if mtime is None or (last_seen is not None and mtime <= last_seen):
                    continue
                if time.time() - mtime < debounce_s:
                    continue
                self.reload(PolicyReloadRequest(path=self._path, source="watcher"))
                last_seen = mtime

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

    def _call_loader(self, path: str | None) -> Policy:
        try:
            return self._loader(path)
        except TypeError:
            # Support zero-arg loader used in tests
            return self._loader()


def get_policy_store() -> PolicyStore:
    # simple singleton for convenience
    global _DEFAULT_STORE
    try:
        return _DEFAULT_STORE
    except NameError:
        _DEFAULT_STORE = PolicyStore()
        return _DEFAULT_STORE
