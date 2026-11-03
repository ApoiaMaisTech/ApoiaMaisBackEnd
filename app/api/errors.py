"""Códigos de erro e respostas padronizadas da API.

Toda resposta de erro tem o formato de ErrorResponse. O `code` é o contrato
estável com o frontend; `message` é só texto para exibição.
"""
from typing import Any

from fastapi import HTTPException

from app.application.common.api_response import ErrorResponse

# código padrão para cada status quando quem levantou o erro não definiu um
DEFAULT_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}

# mensagens em português para os erros que o Starlette gera sozinho (rota inexistente etc.)
DEFAULT_MESSAGES: dict[int, str] = {
    400: "Requisição inválida.",
    401: "Não autenticado.",
    403: "Acesso negado.",
    404: "Recurso não encontrado.",
    405: "Método não permitido.",
    406: "Formato de resposta não suportado.",
    409: "Conflito com dados existentes.",
    413: "Requisição grande demais.",
    415: "Tipo de conteúdo não suportado.",
    422: "Dados inválidos.",
    429: "Muitas requisições. Tente novamente mais tarde.",
    500: "Erro interno do servidor.",
    503: "Serviço temporariamente indisponível.",
}


def default_code(status_code: int) -> str:
    return DEFAULT_CODES.get(status_code, f"HTTP_{status_code}")


def default_message(status_code: int) -> str:
    return DEFAULT_MESSAGES.get(status_code, "Erro na requisição.")


class ApiError(HTTPException):
    """HTTPException com código estável. Use nas dependências e rotas da API."""

    def __init__(
        self,
        status_code: int,
        message: str | None = None,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=message or default_message(status_code), headers=headers)
        self.code = code or default_code(status_code)


def _doc(description: str) -> dict[str, Any]:
    return {"model": ErrorResponse, "description": description}


# respostas de erro documentadas no OpenAPI (o frontend gera tipos a partir delas)
ERROR_401 = {401: _doc("Não autenticado: token ausente, inválido ou expirado (UNAUTHORIZED, TOKEN_EXPIRED, TOKEN_INVALID)")}
ERROR_403 = {403: _doc("Perfil sem permissão para esta ação (FORBIDDEN)")}
ERROR_404 = {404: _doc("Recurso não encontrado")}
ERROR_409 = {409: _doc("Conflito com dados existentes")}

COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: _doc("Dados de entrada inválidos (VALIDATION_ERROR); `errors` traz um item por campo"),
    429: _doc("Limite de requisições atingido (RATE_LIMITED); veja o header Retry-After"),
    500: _doc("Erro inesperado (INTERNAL_ERROR); nenhum detalhe interno é exposto"),
    503: _doc("Banco ou dependência indisponível (SERVICE_UNAVAILABLE)"),
}

PROTECTED_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {**ERROR_401, **ERROR_403}
