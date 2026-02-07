import json
from pathlib import Path

import pytest

from src.tools.timeout_tuner import (
    _percentile,
    suggest_timeouts,
    format_policy_snippet,
    _read_csv,
    _read_json,
)


def test_percentile_basic():
    assert _percentile([100, 200, 300, 400], 0.75) == 400  # ceil index on sorted list


def test_suggest_timeouts_clamped_and_warns():
    latencies = [100, 120, 130]  # small sample triggers warning
    suggestion = suggest_timeouts(latencies, percentile=0.9, provider_min_ms=150, provider_max_ms=500)
    assert suggestion.sample_count == 3
    assert "low_sample_count:3" in suggestion.warnings
    assert suggestion.provider_timeout_ms >= 150
    assert suggestion.e2e_timeout_ms >= suggestion.provider_timeout_ms


def test_format_policy_snippet():
    suggestion = suggest_timeouts([100, 150, 200, 250], percentile=0.5, provider_min_ms=100)
    snippet = format_policy_snippet(suggestion)
    assert "timeouts:" in snippet
    assert "provider_timeout_ms" in snippet


def test_read_csv(tmp_path: Path):
    path = tmp_path / "lat.csv"
    path.write_text("latency_ms\n100\n200\n", encoding="utf-8")
    vals = _read_csv(path)
    assert vals == [100.0, 200.0]


def test_read_json_array(tmp_path: Path):
    path = tmp_path / "lat.json"
    path.write_text(json.dumps([100, 150, 175.5]), encoding="utf-8")
    vals = _read_json(path)
    assert vals == [100.0, 150.0, 175.5]


def test_read_json_objects(tmp_path: Path):
    path = tmp_path / "lat.json"
    path.write_text(json.dumps([{"latency_ms": 111}, {"latency_ms": "bad"}, 222]), encoding="utf-8")
    vals = _read_json(path)
    assert vals == [111.0, 222.0]
