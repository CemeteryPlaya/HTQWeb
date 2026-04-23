"""Structured logging — reusable across all services."""

import logging
import structlog


STANDARD_EVENTS = {
    "service_startup",
    "service_shutdown",
    "request_received",
    "request_completed",
    "request_failed",
    "dramatiq_task_received",
    "dramatiq_task_completed",
    "dramatiq_task_failed",
    "db_query_slow",
    "file_uploaded",
    "file_downloaded",
    "file_deleted",
}


def configure_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
