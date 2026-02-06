import pytest

from src.config import Settings
import os


def test_parse_default_models_from_string():
    settings = Settings(default_models="m1, m2 ,m3")
    assert settings.default_models == ["m1", "m2", "m3"]


def test_parse_default_models_rejects_empty():
    with pytest.raises(ValueError):
        Settings(default_models=" , ", _env_file=None)


def test_positive_fields_validation():
    with pytest.raises(ValueError):
        Settings(provider_timeout_ms=0)

    with pytest.raises(ValueError):
        Settings(e2e_timeout_ms=-1)


def test_settings_default_prompt_limit():
    os.environ.pop("MAX_PROMPT_CHARS", None)
    settings = Settings(_env_file=None)
    assert settings.max_prompt_chars == 8000
