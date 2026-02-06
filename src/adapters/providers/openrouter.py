from __future__ import annotations

import time
from typing import List, Tuple

import httpx

from src.contracts.errors import ErrorEnvelope
from src.adapters.providers.transport import get_client

import json
from pathlib import Path

def load_python_code_format_preamble() -> str:
    """Charge le prompt formaté pour génération de code Python + tests"""
    config_path = Path(__file__).parent.parent.parent / "config" / "rules" / "scoring.json"

    with open(config_path) as f:
        config = json.load(f)
    
    # Reconstruit le prompt complet à partir de la config
    preamble = f"{config['system_prompt']}\n\n"
    preamble += config['critical_output_format'] + "\n\n"
    preamble += "STRICT RULES:\n" + "\n".join(config['strict_rules']) + "\n\n"
    preamble += f"EXAMPLE OF CORRECT OUTPUT:\n{json.dumps(config['example_correct'], indent=2)}\n\n"
    preamble += config['output_instruction']
    
    return preamble

STRUCTURED_PREAMBLE = (
    "You must reply in strict sections: "
    "TREE (folder structure only), "
    "CODE (one single Python file that includes the app code AND its unit tests; "
    "output exactly one fenced ```python``` block; include paths as comments), "
    "RULES (3-7 bullet rules). "
    "No prose outside these sections; keep it concise."
)

_PYTHON_PREAMBLE_CACHE: str | None = None


def get_python_code_format_preamble() -> str:
    global _PYTHON_PREAMBLE_CACHE
    if _PYTHON_PREAMBLE_CACHE is None:
        try:
            _PYTHON_PREAMBLE_CACHE = load_python_code_format_preamble()
        except FileNotFoundError as exc:  # pragma: no cover - defensive
            raise RuntimeError("scoring preamble configuration missing") from exc
    return _PYTHON_PREAMBLE_CACHE


# Backward compatibility: expose a lazy attribute without eager file IO
def __getattr__(name: str):
    if name == "PYTHON_CODE_FORMAT_PREAMBLE":
        return get_python_code_format_preamble()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _build_messages(prompt: str, system_preamble: str | None) -> List[dict]:
    messages = []
    if system_preamble:
        messages.append({"role": "system", "content": system_preamble})
    messages.append({"role": "user", "content": prompt})
    return messages


async def call_model(
    prompt: str,
    model: str,
    request_id: str,
    system_preamble: str | None = None,
    provider_timeout_ms: int | None = None,
) -> Tuple[str | None, int | None, ErrorEnvelope | None]:
    client = get_client(timeout_ms=provider_timeout_ms)
    payload = {
        "model": model,
        "messages": _build_messages(prompt, system_preamble),
        "stream": False,
    }
    headers = {"x-request-id": request_id}

    start = time.perf_counter()
    try:
        response = await client.post("/chat/completions", json=payload, headers=headers)
        latency_ms = int((time.perf_counter() - start) * 1000)
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return (
                None,
                latency_ms,
                ErrorEnvelope(
                    type="invalid_response",
                    message="Invalid response payload",
                    retryable=False,
                    status_code=response.status_code,
                ),
            )
        return content, latency_ms, None
    except httpx.TimeoutException as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return (
            None,
            latency_ms,
            ErrorEnvelope(type="timeout", message=str(exc), retryable=True, status_code=None),
        )
    except httpx.HTTPStatusError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        status_code = exc.response.status_code
        error_type = "rate_limited" if status_code == 429 else "http_error"
        retryable = status_code >= 500 or status_code == 429
        return (
            None,
            latency_ms,
            ErrorEnvelope(
                type=error_type,
                message=str(exc),
                retryable=retryable,
                status_code=status_code,
            ),
        )
    except (ValueError, httpx.RequestError) as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        error_type = "invalid_response" if isinstance(exc, ValueError) else "http_error"
        return (
            None,
            latency_ms,
            ErrorEnvelope(type=error_type, message=str(exc), retryable=False, status_code=None),
        )
