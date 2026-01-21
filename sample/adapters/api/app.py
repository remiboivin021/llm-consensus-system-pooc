from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from sample.adapters.api.middleware import RequestContextMiddleware
from sample.adapters.api.routes import router
from sample.config import get_settings
from sample.adapters.observability.logging import configure_logging
from sample.adapters.observability.tracing import configure_tracing
from sample.adapters.providers.transport import close_client

settings = get_settings()

tracer_provider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _, log_provider = configure_logging(
        settings.service_name, settings.log_level, settings.otel_exporter_otlp_endpoint
    )
    try:
        yield
    finally:
        try:
            await close_client()
        except RuntimeError:
            pass
        if log_provider:
            log_provider.shutdown()
        if tracer_provider:
            tracer_provider.shutdown()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.include_router(router)

tracer_provider = configure_tracing(
    app, settings.service_name, settings.otel_exporter_otlp_endpoint
)
