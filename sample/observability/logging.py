from __future__ import annotations

import logging
import sys

import structlog

try:
    from opentelemetry.exporter.otlp.proto.http.log_exporter import OTLPLogExporter

    _OTLP_EXPORTER_SOURCE = "public"
except ImportError:  # fallback for older opentelemetry versions
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter  # type: ignore

    _OTLP_EXPORTER_SOURCE = "private"
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource


def _logs_endpoint(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    return endpoint if endpoint.endswith("/v1/logs") else f"{endpoint}/v1/logs"


def _configure_otlp_logging(
    level: int, service_name: str, endpoint: str | None
) -> LoggerProvider | None:
    if not endpoint:
        return None
    try:
        resource = Resource.create({"service.name": service_name})
        logger_provider = LoggerProvider(resource=resource)
        exporter = OTLPLogExporter(endpoint=_logs_endpoint(endpoint))
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        handler = LoggingHandler(level=level, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
        if _OTLP_EXPORTER_SOURCE == "private":
            logging.getLogger(__name__).warning("otlp_log_exporter_private_path_in_use")
        return logger_provider
    except Exception as exc:
        logging.getLogger(__name__).warning("otlp_logging_setup_failed: %s", exc)
        return None


def configure_logging(
    service_name: str, log_level: str = "INFO", otlp_endpoint: str | None = None
) -> tuple[structlog.stdlib.BoundLogger, LoggerProvider | None]:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    logger_provider = _configure_otlp_logging(level, service_name, otlp_endpoint)
    return structlog.get_logger().bind(service=service_name), logger_provider


def get_logger(**kwargs) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(**kwargs)
