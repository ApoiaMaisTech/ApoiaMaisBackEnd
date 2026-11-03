from .base import DomainException


class InvalidCredentialsException(DomainException):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    default_message = "Email ou senha inválidos."
