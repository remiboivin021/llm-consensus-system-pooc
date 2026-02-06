"""LLM provider clients (httpx-based)."""
from src.adapters.providers.openrouter import call_model
from src.adapters.providers.transport import close_client

__all__ = [
    "call_model",
    "close_client"
]