from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import Settings


SETTINGS_ENV_KEYS = [
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "DEFAULT_MODELS",
    "POLICY_FILE",
    "PROVIDER_TIMEOUT_MS",
    "E2E_TIMEOUT_MS",
    "MAX_PROMPT_CHARS",
    "MAX_MODELS",
    "LOG_LEVEL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "SERVICE_NAME",
]


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in SETTINGS_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_settings_loads_policy_file_from_env(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
policy_id: tmp-policy
guardrails:
  request:
    prompt_min_chars: 1
    prompt_max_chars: 10
    models:
      min_models: 1
      max_models: 2
      unique_required: true
      allowed_models: '*'
""",
        encoding="utf-8",
    )
    env_file = tmp_path / "env"
    env_file.write_text(f"POLICY_FILE={policy_path}\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.policy_file == str(policy_path)


def test_settings_rejects_missing_policy_file(tmp_path: Path) -> None:
    env_file = tmp_path / "env"
    env_file.write_text("POLICY_FILE=policies/missing.policy.yaml\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Policy file not found"):
        Settings(_env_file=env_file)


def test_settings_requires_integer_max_prompt(tmp_path: Path) -> None:
    env_file = tmp_path / "env"
    env_file.write_text("MAX_PROMPT_CHARS=10000docke\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        Settings(_env_file=env_file)
