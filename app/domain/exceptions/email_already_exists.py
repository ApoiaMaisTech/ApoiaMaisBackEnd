from .base import DomainException


class EmailAlreadyExistsException(DomainException):
    status_code = 409
    code = "EMAIL_ALREADY_EXISTS"
    default_message = "Este email já está cadastrado."
