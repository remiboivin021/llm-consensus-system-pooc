from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from sample.config import get_settings
from sample.contracts.errors import ErrorEnvelope
from sample.contracts.request import ConsensusRequest
from sample.contracts.response import ConsensusResult
from sample.adapters.orchestration.orchestrator import OrchestrationError, Orchestrator
from sample.adapters.observability.metrics import CONTENT_TYPE_LATEST, render_metrics

router = APIRouter()
orchestrator = Orchestrator()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    get_settings()
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(render_metrics(), media_type=CONTENT_TYPE_LATEST)


@router.post("/v1/consensus", response_model=ConsensusResult)
async def consensus(consensus_request: ConsensusRequest, request: Request):
    request_id = getattr(request.state, "request_id", None) or consensus_request.request_id

    if len(consensus_request.prompt) > orchestrator.settings.max_prompt_chars:
        envelope = ErrorEnvelope(
            type="config_error", message="Prompt too long", retryable=False, status_code=400
        )
        return JSONResponse(status_code=400, content=envelope.model_dump())

    try:
        result = await orchestrator.run(consensus_request, request_id)
    except OrchestrationError as exc:
        envelope = exc.envelope
        status = envelope.status_code or 500
        return JSONResponse(status_code=status, content=envelope.model_dump())

    return result
