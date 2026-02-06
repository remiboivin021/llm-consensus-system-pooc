import json
from pathlib import Path

import pytest

from examples.bench.harness import HarnessConfig, run_harness
from examples.bench.schema import FixtureCase, FixtureFile, ProviderOutput, load_fixture_file


def test_fixture_validation_rejects_length_mismatch():
    with pytest.raises(Exception):
        FixtureCase.model_validate(
            {
                "case_id": "bad-length",
                "prompt": "x",
                "models": ["m1", "m2"],
                "provider_outputs": [{"model": "m1", "content": "one"}],
            }
        )


def test_harness_smoke_fixture(tmp_path):
    fixtures_path = Path("examples/bench/fixtures/smoke.json")
    fixtures = load_fixture_file(fixtures_path)
    result = run_harness(fixtures, HarnessConfig(seed=fixtures.seed))

    summary = result.summary
    assert summary["passed"] == 2
    assert summary["failed"] == 0
    assert summary["gated"] == 1

    case_lookup = {c["case_id"]: c for c in result.to_dict()["cases"]}
    assert case_lookup["majority-pass"]["winner"] == "m1"
    assert case_lookup["pre-gate-too-few-models"]["gate_stage"] == "pre"


def test_harness_deterministic(tmp_path):
    fixtures = FixtureFile(
        seed=42,
        cases=[
            FixtureCase(
                case_id="deterministic",
                prompt="hello",
                models=["m1", "m2"],
                provider_outputs=[
                    ProviderOutput(model="m1", content="foo bar"),
                    ProviderOutput(model="m2", content="foo baz"),
                ],
                expected_winner="m1",
            )
        ],
    )

    r1 = run_harness(fixtures, HarnessConfig(seed=42)).to_dict()
    r2 = run_harness(fixtures, HarnessConfig(seed=42)).to_dict()

    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
