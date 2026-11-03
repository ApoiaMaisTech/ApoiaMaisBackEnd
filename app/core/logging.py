import logging
import re
from uuid import uuid4

import structlog

from app.core.redaction import redact_processor

_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Logs estruturados para structlog e para o logging da biblioteca padrão.

    Todo log carrega o que estiver nas contextvars (correlation_id, event_id...),
    então quem já usa logging.getLogger continua funcionando e ganha os campos.
    """
    shared = _shared_processors()

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(build_formatter(json_logs))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def build_formatter(json_logs: bool = True) -> logging.Formatter:
    """Formatter único dos logs (também usado nos testes de LGPD)."""
    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    return structlog.stdlib.ProcessorFormatter(
        # ExtraAdder: logger.info("...", extra={...}) vira campos do JSON
        foreign_pre_chain=[*_shared_processors(), structlog.stdlib.ExtraAdder()],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            # LGPD: depois do traceback renderizado e antes de sair do processo
            redact_processor,
            renderer,
        ],
    )


def _shared_processors() -> list:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]


def normalize_correlation_id(value: str | None) -> str:
    # valor vindo de fora só é aceito se for curto e sem caracteres estranhos
    if value and _CORRELATION_ID.match(value):
        return value
    return uuid4().hex


def get_correlation_id() -> str:
    value = structlog.contextvars.get_contextvars().get("correlation_id")
    return value or uuid4().hex
