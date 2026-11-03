import logging

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import default_code, default_message
from app.domain.exceptions.base import DomainException

logger = logging.getLogger("apoiamais.errors")


def _current_correlation_id() -> str | None:
    return structlog.contextvars.get_contextvars().get("correlation_id")


# monta a resposta no formato de ErrorResponse (app/application/common/api_response.py)
def error_response(
    status_code: int,
    message: str | None = None,
    errors: list[str] | None = None,
    headers: dict[str, str] | None = None,
    code: str | None = None,
    correlation_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code or default_code(status_code),
            "message": message or default_message(status_code),
            "errors": errors or [],
            "correlation_id": correlation_id or _current_correlation_id(),
        },
        headers=headers,
    )


def _format_validation_error(error: dict) -> str:
    # ignora o prefixo "body"/"query"/"path" e nunca devolve o valor enviado (pode ser senha)
    location = [str(part) for part in error.get("loc", ())[1:]]
    field = ".".join(location) or "request"
    if error.get("type") == "json_invalid":
        return f"{field}: JSON malformado"
    return f"{field}: {error.get('msg', 'valor inválido')}"


# registra excecoes globais mp navegador
def register_exception_handlers(app: FastAPI):

    # usa o construtor base de excecoes como argumento; o status e o code vêm da subclasse
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        return error_response(exc.status_code, exc.message, code=exc.code)

    # HTTPException (401, 403, 404 de rota, 405, 429...) no mesmo formato.
    # ApiError traz `code`; as do Starlette (rota inexistente, 405) usam o padrão do status.
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = getattr(exc, "code", None)
        if code is None:
            # mensagem do próprio Starlette ("Not Found", "Method Not Allowed"): troca pela nossa
            message = default_message(exc.status_code)
        else:
            message = exc.detail if isinstance(exc.detail, str) else None
        return error_response(
            exc.status_code,
            message,
            headers=getattr(exc, "headers", None),
            code=code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=[_format_validation_error(e) for e in exc.errors()],
        )

    # corrida entre duas requisições com o mesmo email, por exemplo
    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        logger.warning("Violação de integridade em %s %s", request.method, request.url.path)
        return error_response(status.HTTP_409_CONFLICT)

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Erro de banco em %s %s", request.method, request.url.path)
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE)

    # qualquer outra coisa: loga o traceback e responde sem detalhes internos.
    # Na prática o CorrelationIdMiddleware captura antes (para manter o correlation id);
    # este handler continua como rede de segurança se o middleware for removido.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR)
