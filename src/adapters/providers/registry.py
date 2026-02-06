from __future__ import annotations

import threading
from typing import Dict, Tuple

from src.adapters.providers.base import ProviderAdapter
from src.errors import LcsError

_providers: Dict[str, ProviderAdapter] = {}
_default_provider_name: str | None = None
_lock = threading.Lock()


def register_provider(provider: ProviderAdapter, *, default: bool = False) -> None:
    """Register a provider adapter. Default provider is unique."""
    global _default_provider_name
    if not provider or not getattr(provider, "name", None):
        raise ValueError("provider must define a non-empty name")
    with _lock:
        if provider.name in _providers:
            raise ValueError(f"provider already registered: {provider.name}")
        if default:
            if _default_provider_name is not None:
                raise ValueError("default provider already registered")
            _default_provider_name = provider.name
        _providers[provider.name] = provider


def get_provider(name: str) -> ProviderAdapter:
    try:
        return _providers[name]
    except KeyError as exc:
        raise LcsError(code="config_error", message=f"unknown provider: {name}") from exc


def resolve_provider(model_name: str, override_name: str | None = None) -> Tuple[ProviderAdapter, str]:
    """
    Resolve which provider to use for a model.
    Priority: explicit override > inline prefix > default provider.
    Inline syntax: \"provider::model_name\".
    Returns (provider, stripped_model_name).
    """
    provider_name = override_name
    stripped_model = model_name

    if "::" in model_name:
        maybe_provider, maybe_model = model_name.split("::", 1)
        if maybe_provider and maybe_model:
            provider_name = provider_name or maybe_provider
            stripped_model = maybe_model

    selected_provider = None
    if provider_name:
        selected_provider = _providers.get(provider_name)
        if selected_provider is None:
            raise LcsError(code="config_error", message=f"unknown provider: {provider_name}")
    else:
        if _default_provider_name is None:
            raise LcsError(code="config_error", message="no default provider registered")
        selected_provider = _providers.get(_default_provider_name)
        if selected_provider is None:
            raise LcsError(code="config_error", message="default provider not found")

    if not selected_provider.supports(stripped_model):
        raise LcsError(
            code="config_error",
            message=f"provider {selected_provider.name} does not support model {stripped_model}",
        )

    return selected_provider, stripped_model


def clear_registry() -> None:
    """Testing helper to reset registry."""
    global _default_provider_name
    with _lock:
        _providers.clear()
        _default_provider_name = None
