# Python Usage

This guide shows how to call LCS from your own Python code, tune consensus strategies, and interpret results.

The primary entrypoint is `LcsClient`. Build a `ConsensusRequest` with a prompt and a list of model identifiers, then run the client asynchronously. When `strategy` is omitted, `majority_cosine` is used, which embeds outputs and picks the most central response by cosine similarity.

Available strategies are `majority_cosine` (embedding-based majority vote), `score_preferred` (use quality scores when available, otherwise fall back to majority), and `scoring` (always pick the highest quality score). Retrieve names with `src.list_strategies()`. All judges return a `ConsensusResult` containing `winner`, `confidence`, `method`, optional `scores`, and optional raw `responses`.

Flags on `ConsensusRequest` adjust behaviour: set `include_raw` to keep per-model responses in the result, set `include_scores` to compute code-quality scores using radon/pycodestyle/pydocstyle/vulture/bandit, and set `normalize_output` to prepend a structured system preamble that enforces sectioned output. The `models` field defaults to `DEFAULT_MODELS` from configuration; validation enforces the configured maximum.

Example usage:

```python
import asyncio
from src import LcsClient, ConsensusRequest

async def run():
    req = ConsensusRequest(
        prompt="Write a pure Python Fibonacci function with one test case.",
        models=["qwen/qwen3-coder:free", "mistralai/devstral-2512:free"],
        include_scores=True,
    )
    result = await LcsClient().run(req, strategy="score_preferred")
    print(result.winner, result.confidence, result.score_stats)

asyncio.run(run())
```

Errors from provider calls surface as `LcsError` with codes such as `provider_error`, `timeout`, or `config_error`. In shadow or soft gating, the result may set `gated=True` and include `gate_reason`; consumers should check these flags before trusting the winner.

Validate integration by running `poetry run pytest tests/unit/test_client.py tests/unit/test_orchestrator_branches.py tests/unit/test_consensus.py`. For live calls, export a valid `OPENROUTER_API_KEY` and confirm the snippet above returns a winner and nonzero confidence; to avoid network calls in CI, monkeypatch `fetch_provider_result` as shown in `tests/unit/test_orchestrator_runs_with_scores`.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
