from typing import Generic, TypeVar

from pydantic import BaseModel

# define os dados de retorno tem a tipagem flexivel
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    # modelo de retorno padronizado 
    success: bool
    message: str
    data: T | None = None
    errors: list[str] = []
