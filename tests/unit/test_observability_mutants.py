import logging

import pytest
from fastapi import FastAPI

from src.adapters.observability import logging as otlp_logging
from src.adapters.observability import tracing as otlp_tracing


def test_configure_logging_no_endpoint_returns_none_provider():
    logger, provider = otlp_logging.configure_logging("svc", otlp_endpoint=None)
    assert logger is not None
    assert provider is None


def test_logs_endpoint_adds_suffix():
    assert otlp_logging._logs_endpoint("http://x:4318") == "http://x:4318/v1/logs"


def test_configure_tracing_no_endpoint():
    app = FastAPI()
    provider = otlp_tracing.configure_tracing(app, "svc", endpoint=None)
    assert provider is None


def test_configure_logging_twice_idempotent(monkeypatch):
    calls = {"exporter": 0}

    class DummyExporter:
        def __init__(self, endpoint=None, **kwargs):
            calls["exporter"] += 1
            self.endpoint = endpoint
        def shutdown(self): ...
        def force_flush(self, *a, **k): return True

    monkeypatch.setattr(otlp_logging, "OTLPLogExporter", DummyExporter)
    logger1, provider1 = otlp_logging.configure_logging("svc", otlp_endpoint="http://collector:4318")
    logger2, provider2 = otlp_logging.configure_logging("svc", otlp_endpoint="http://collector:4318")
    assert logger1 is not None and logger2 is not None
    assert calls["exporter"] >= 1


def test_configure_tracing_handles_exporter_exception(monkeypatch):
    monkeypatch.setattr(
        otlp_tracing, "OTLPSpanExporter", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    app = FastAPI()
    provider = otlp_tracing.configure_tracing(app, "svc", endpoint="http://collector:4318")
    assert provider is None


def test_traces_endpoint_adds_suffix():
    assert otlp_tracing._traces_endpoint("http://x:4318") == "http://x:4318/v1/traces"
