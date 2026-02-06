import logging

from fastapi import FastAPI

from src.adapters.observability import logging as otlp_logging
from src.adapters.observability import tracing as otlp_tracing


def test_logging_uses_versioned_otlp_path(monkeypatch):
    captured = {}

    def fake_logs_endpoint(endpoint: str) -> str:
        captured["raw_endpoint"] = endpoint
        return "normalized-logs-endpoint"

    class DummyExporter:
        def __init__(self, endpoint=None, **kwargs):
            captured["endpoint"] = endpoint

        def export(self, *args, **kwargs):
            return None

        def shutdown(self):
            return None

        def force_flush(self, *args, **kwargs):
            return True

    class DummyProcessor:
        def __init__(self, exporter):
            self.exporter = exporter

        def emit(self, *args, **kwargs):
            return None

        def shutdown(self):
            return None

        def force_flush(self, *args, **kwargs):
            return True

    class DummyHandler:
        def __init__(self, level, logger_provider):
            self.level = level
            self.logger_provider = logger_provider

        def handle(self, record):
            return None

    monkeypatch.setattr(otlp_logging, "_logs_endpoint", fake_logs_endpoint)
    monkeypatch.setattr(otlp_logging, "OTLPLogExporter", DummyExporter)
    monkeypatch.setattr(otlp_logging, "BatchLogRecordProcessor", DummyProcessor)
    monkeypatch.setattr(otlp_logging, "LoggingHandler", DummyHandler)

    otlp_logging._configure_otlp_logging(
        level=logging.INFO, service_name="svc", endpoint="http://collector:4318"
    )

    assert captured["raw_endpoint"] == "http://collector:4318"
    assert captured["endpoint"] == "normalized-logs-endpoint"


def test_tracing_uses_versioned_otlp_path(monkeypatch):
    captured = {}

    def fake_traces_endpoint(endpoint: str) -> str:
        captured["raw_endpoint"] = endpoint
        return "normalized-traces-endpoint"

    class DummyExporter:
        def __init__(self, endpoint=None, **kwargs):
            captured["endpoint"] = endpoint

        def export(self, *args, **kwargs):
            return None

        def shutdown(self):
            return None

        def force_flush(self, *args, **kwargs):
            return True

    class DummyProcessor:
        def __init__(self, exporter):
            self.exporter = exporter

        def on_start(self, *args, **kwargs):
            return None

        def on_end(self, *args, **kwargs):
            return None

        def shutdown(self):
            return None

        def force_flush(self, *args, **kwargs):
            return True

    class DummyHTTPXInstrumentor:
        def instrument(self):
            return None

    class DummyFastAPIInstrumentor:
        def instrument_app(self, app: FastAPI):
            captured["instrumented_app"] = app

    monkeypatch.setattr(otlp_tracing, "_traces_endpoint", fake_traces_endpoint)
    monkeypatch.setattr(otlp_tracing, "OTLPSpanExporter", DummyExporter)
    monkeypatch.setattr(otlp_tracing, "BatchSpanProcessor", DummyProcessor)
    monkeypatch.setattr(otlp_tracing, "FastAPIInstrumentor", DummyFastAPIInstrumentor())
    monkeypatch.setattr(otlp_tracing, "HTTPXClientInstrumentor", lambda: DummyHTTPXInstrumentor())

    app = FastAPI()
    otlp_tracing.configure_tracing(app, "svc", "http://collector:4318")

    assert captured["raw_endpoint"] == "http://collector:4318"
    assert captured["endpoint"] == "normalized-traces-endpoint"
    assert captured["instrumented_app"] is app


def test_logs_endpoint_normalization():
    assert otlp_logging._logs_endpoint("http://x:4318/") == "http://x:4318/v1/logs"
    assert otlp_logging._logs_endpoint("http://x:4318/v1/logs") == "http://x:4318/v1/logs"


def test_configure_logging_swallows_exporter_errors(monkeypatch):
    def boom_exporter(*args, **kwargs):
        raise RuntimeError("fail exporter")

    monkeypatch.setattr(otlp_logging, "OTLPLogExporter", boom_exporter)
    logger, provider = otlp_logging.configure_logging("svc", otlp_endpoint="http://bad")
    assert logger is not None
    assert provider is None


def test_traces_endpoint_normalization():
    assert otlp_tracing._traces_endpoint("http://x:4318/") == "http://x:4318/v1/traces"
    assert otlp_tracing._traces_endpoint("http://x:4318/v1/traces") == "http://x:4318/v1/traces"


def test_configure_tracing_handles_exporter_failure(monkeypatch):
    monkeypatch.setattr(otlp_tracing, "OTLPSpanExporter", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    app = FastAPI()
    provider = otlp_tracing.configure_tracing(app, "svc", "http://bad")
    assert provider is None
