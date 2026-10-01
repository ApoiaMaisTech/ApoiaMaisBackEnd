from .base import DomainException
class InvalidCredentialsException(DomainException):
    status_code = 401
    default_message = "Invalid credentials"
