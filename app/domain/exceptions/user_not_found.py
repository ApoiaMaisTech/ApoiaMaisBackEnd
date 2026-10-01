from .base import DomainException
class UserNotFoundException(DomainException):
    status_code = 404
    default_message = "User not found"
