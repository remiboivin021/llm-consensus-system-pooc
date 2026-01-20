from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import httpx
import typer

from sample.config import get_settings
from sample.contracts.request import ConsensusRequest
from sample.contracts.response import ConsensusResult, Timing
from sample.core.consensus import compute_consensus
from sample.core.models import ProviderResult, build_model_responses, fetch_provider_result
from sample.providers.transport import close_client

app = typer.Typer(help="LLM consensus CLI")


async def _run_consensus(
    prompt: str, models: list[str], mode: str, include_raw: bool, normalize_output: bool
) -> ConsensusResult:
    request_id = str(uuid4())
    tasks = [
        fetch_provider_result(prompt, model, request_id, normalize_output) for model in models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    provider_results: list[ProviderResult | Exception] = []
    for result in results:
        provider_results.append(result)

    model_responses = build_model_responses(models, provider_results)

    winner, confidence, method = compute_consensus(model_responses)
    await close_client()
    return ConsensusResult(
        request_id=request_id,
        winner=winner,
        confidence=confidence,
        responses=[] if not include_raw else model_responses,
        method=method,
        timing=Timing(e2e_ms=0),
    )


@app.command()
def consensus(
    prompt: str = typer.Option(..., help="Prompt to send to the models"),
    models: str = typer.Option(
        None, help="Comma-separated list of models. Defaults to config DEFAULT_MODELS."
    ),
    mode: str = typer.Option("majority", help="Consensus mode."),
    include_raw: bool = typer.Option(True, help="Return raw responses (kept for API parity)."),
    normalize_output: bool = typer.Option(
        False, help="Inject a structured preamble (TREE/RULES/FILES) before the prompt."
    ),
) -> None:
    if mode != "majority":
        typer.echo("Unsupported mode: only 'majority' is implemented.")
        raise typer.Exit(code=1)

    settings = get_settings()
    model_list = [
        m.strip() for m in (models.split(",") if models else settings.default_models) if m.strip()
    ]
    request = ConsensusRequest(
        prompt=prompt,
        models=model_list,
        mode=mode,
        include_raw=include_raw,
        normalize_output=normalize_output,
    )
    api_url = os.environ.get("API_URL")

    if api_url:
        url = api_url.rstrip("/") + "/v1/consensus"
        with httpx.Client() as client:
            response = client.post(url, json=request.model_dump())
            response.raise_for_status()
            typer.echo(json.dumps(response.json(), indent=2))
    else:
        result = asyncio.run(
            _run_consensus(
                request.prompt,
                request.models,
                request.mode,
                request.include_raw,
                request.normalize_output,
            )
        )
        typer.echo(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    app()
