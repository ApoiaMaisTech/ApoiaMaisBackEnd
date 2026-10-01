from .base import DomainException
class EmailAlreadyExistsException(DomainException):
    status_code = 409
    default_message = "Email already exists"
