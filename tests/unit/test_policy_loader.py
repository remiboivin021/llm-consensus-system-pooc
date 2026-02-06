import time
import pytest

from src.policy.loader import PolicyStore, load_policy


def test_load_default_policy_uses_expected_max_prompt(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        """
policy_id: default-v1
guardrails:
  request:
    prompt_min_chars: 1
    prompt_max_chars: 8000
    models:
      min_models: 1
      max_models: 2
      unique_required: true
      allowed_models: '*'
""",
        encoding="utf-8",
    )
    policy = load_policy(str(path))
    assert policy.guardrails.request.prompt_max_chars == 8000


def test_load_policy_missing_file_raises(tmp_path, monkeypatch):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        load_policy(str(missing))

    monkeypatch.setenv("POLICY_FILE", str(missing))
    with pytest.raises(FileNotFoundError):
        load_policy(None)


def test_load_policy_env_override(monkeypatch, tmp_path):
    data = """
policy_id: env-policy
guardrails:
  request:
    prompt_min_chars: 1
    prompt_max_chars: 10
    models:
      min_models: 1
      max_models: 2
      unique_required: true
      allowed_models: '*'
"""
    path = tmp_path / "policy.yaml"
    path.write_text(data, encoding="utf-8")
    monkeypatch.setenv("POLICY_FILE", str(path))

    policy = load_policy(None)
    assert policy.policy_id == "env-policy"
    assert policy.guardrails.request.prompt_max_chars == 10


def test_load_policy_builtin_fallback_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("POLICY_FILE", raising=False)
    monkeypatch.setattr("src.policy.loader.default_policy_path", lambda: str(tmp_path / "missing.yaml"))

    policy = load_policy()
    assert policy.policy_id == "default-v1"
    assert policy.guardrails.request.prompt_max_chars == 8000


def test_policy_store_reload_success(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        """
policy_id: reload-1
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
    store = PolicyStore(str(path))
    result = store.reload()
    assert result.status == "success"
    assert store.current().policy_id == "reload-1"


def test_policy_store_reload_invalid_yaml(tmp_path):
    path = tmp_path / "good.yaml"
    path.write_text(
        """
policy_id: good
guardrails:
  request:
    prompt_min_chars: 1
    prompt_max_chars: 5
    models:
      min_models: 1
      max_models: 1
      unique_required: true
      allowed_models: '*'
""",
        encoding="utf-8",
    )
    store = PolicyStore(str(path))

    path.write_text(":::", encoding="utf-8")
    result = store.reload()
    assert result.status == "failure"
    assert result.error_reason in {"invalid_yaml", "validation_error"}
    assert store.current().policy_id == "good"


def test_policy_store_watcher_triggers(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        """
policy_id: watch-1
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
    store = PolicyStore(str(path))
    store.start_watcher(poll_interval_s=0.05, debounce_s=0.0)
    time.sleep(0.1)
    path.write_text(path.read_text().replace("watch-1", "watch-2"), encoding="utf-8")
    time.sleep(0.2)
    store.stop_watcher()
    assert store.current().policy_id == "watch-2"

