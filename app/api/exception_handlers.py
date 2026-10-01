import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions.base import DomainException

logger = logging.getLogger("apoiamais.errors")


# monta a resposta no mesmo formato do ApiResponse
def error_response(
    status_code: int,
    message: str,
    errors: list[str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "errors": errors or []},
        headers=headers,
    )


def _format_validation_error(error: dict) -> str:
    # ignora o prefixo "body"/"query"/"path" e nunca devolve o valor enviado (pode ser senha)
    location = [str(part) for part in error.get("loc", ())[1:]]
    field = ".".join(location) or "request"
    return f"{field}: {error.get('msg', 'valor inválido')}"


# registra excecoes globais mp navegador
def register_exception_handlers(app: FastAPI):

    # usa o construtor base de excecoes como argumento; o status vem da subclasse
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        return error_response(exc.status_code, exc.message)

    # HTTPException (401, 403, 404 de rota, 405, 429...) no mesmo formato
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Erro na requisição."
        return error_response(exc.status_code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Dados inválidos.",
            [_format_validation_error(e) for e in exc.errors()],
        )

    # corrida entre duas requisições com o mesmo email, por exemplo
    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        logger.warning("Violação de integridade em %s %s", request.method, request.url.path)
        return error_response(status.HTTP_409_CONFLICT, "Conflito com dados existentes.")

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Erro de banco em %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Serviço temporariamente indisponível.",
        )

    # qualquer outra coisa: loga o traceback e responde sem detalhes internos
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Erro interno do servidor.",
        )
