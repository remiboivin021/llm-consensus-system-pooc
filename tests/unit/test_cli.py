import pytest
import typer

from sample.cli.main import _run_consensus, consensus
from sample.contracts.response import ConsensusResult, Timing
from sample.core.models import ProviderResult


@pytest.mark.asyncio
async def test_cli_offline_consensus_respects_include_raw(monkeypatch):
    async def fake_fetch_provider_result(prompt, model, request_id, normalize_output):
        return ProviderResult(model=model, content=f"resp-{model}", latency_ms=10, error=None)

    monkeypatch.setattr("sample.cli.main.fetch_provider_result", fake_fetch_provider_result)
    result = await _run_consensus(
        "hi", ["m1", "m2"], mode="majority", include_raw=False, normalize_output=False
    )

    assert result.winner in {"m1", "m2"}
    assert result.responses == []


@pytest.mark.asyncio
async def test_cli_normalize_output_passes_preamble(monkeypatch):
    captured = {}

    async def fake_fetch_provider_result(prompt, model, request_id, normalize_output):
        captured["normalize_output"] = normalize_output
        return ProviderResult(model=model, content=f"resp-{model}", latency_ms=10, error=None)

    monkeypatch.setattr("sample.cli.main.fetch_provider_result", fake_fetch_provider_result)
    result = await _run_consensus(
        "hi", ["m1"], mode="majority", include_raw=True, normalize_output=True
    )

    assert result.responses
    assert captured["normalize_output"] is True


def test_cli_rejects_unsupported_mode():
    with pytest.raises(typer.Exit) as excinfo:
        consensus(prompt="hi", models="m1", mode="debate", include_raw=True, normalize_output=False)

    assert excinfo.value.exit_code == 1


def test_cli_offline_path_runs_local_consensus(monkeypatch, capsys):
    monkeypatch.delenv("API_URL", raising=False)

    called = {}

    async def fake_run(prompt, models, mode, include_raw, normalize_output):
        called["args"] = (prompt, tuple(models), mode, include_raw, normalize_output)
        return ConsensusResult(
            request_id="req-123",
            winner="m1",
            confidence=1.0,
            responses=[],
            method="majority",
            timing=Timing(e2e_ms=0),
        )

    monkeypatch.setattr("sample.cli.main._run_consensus", fake_run)

    consensus(prompt="hi", models="m1", mode="majority", include_raw=True, normalize_output=False)

    out = capsys.readouterr().out
    assert called["args"] == ("hi", ("m1",), "majority", True, False)
    assert '"winner": "m1"' in out
