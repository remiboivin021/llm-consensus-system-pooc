"""LLM provider clients (httpx-based)."""
from sample.adapters.providers.openrouter import call_model
from sample.adapters.providers.transport import close_client

__all__ = [
    "call_model",
    "close_client"
]