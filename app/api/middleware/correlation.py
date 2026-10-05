import logging
import time

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import normalize_correlation_id

HEADER = "X-Correlation-ID"
access_logger = logging.getLogger("apoiamais.access")
_HEADER_BYTES = HEADER.lower().encode()


class CorrelationIdMiddleware:
    """Propaga (ou gera) o X-Correlation-ID, coloca em todos os logs e registra o acesso."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", []):
            if name == _HEADER_BYTES:
                incoming = value.decode("latin-1")
                break
        correlation_id = normalize_correlation_id(incoming)

        status_code = 500
        started = time.perf_counter()

        async def send_with_header(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[HEADER] = correlation_id
            await send(message)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            await self.app(scope, receive, send_with_header)
        finally:
            # log de acesso estruturado (sem query string nem corpo: podem ter dados pessoais)
            access_logger.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            structlog.contextvars.clear_contextvars()
