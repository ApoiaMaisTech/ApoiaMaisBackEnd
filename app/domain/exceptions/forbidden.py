from .base import DomainException
class ForbiddenActionException(DomainException):
    status_code = 403
    default_message = "Ação não permitida."
