from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

# define os dados de retorno tem a tipagem flexivel
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    # modelo de retorno padronizado
    success: bool
    message: str
    data: T | None = None
    errors: list[str] = []


class ErrorResponse(BaseModel):
    """Formato único de TODA resposta de erro da API (4xx e 5xx).

    - `code`: identificador estável, em inglês e MAIÚSCULAS (contrato com o frontend).
    - `message`: texto para exibir ao usuário (pode mudar sem aviso).
    - `errors`: detalhes por campo, só em erros de validação ("campo: problema").
    - `correlation_id`: o mesmo do header X-Correlation-ID, para achar o log.
    """

    success: Literal[False] = False
    code: str = Field(examples=["VALIDATION_ERROR"])
    message: str = Field(examples=["Dados inválidos."])
    errors: list[str] = Field(default_factory=list, examples=[["email: value is not a valid email address"]])
    correlation_id: str | None = Field(default=None, examples=["4f9c2b7e1a3d4c5b8e6f7a8b9c0d1e2f"])
