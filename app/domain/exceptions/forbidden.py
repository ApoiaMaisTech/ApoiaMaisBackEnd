from .base import DomainException


class ForbiddenActionException(DomainException):
    status_code = 403
    code = "FORBIDDEN"
    default_message = "Ação não permitida."
