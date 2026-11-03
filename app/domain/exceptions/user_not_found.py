from .base import DomainException


class UserNotFoundException(DomainException):
    status_code = 404
    code = "USER_NOT_FOUND"
    default_message = "Usuário não encontrado."
