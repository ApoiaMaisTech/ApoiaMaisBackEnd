from .base import DomainException


class StageNotFoundException(DomainException):
    status_code = 404
    default_message = "Fase não encontrada."


class AiImageNotFoundException(DomainException):
    status_code = 404
    default_message = "Imagem não encontrada."


class AiImageNotReadyException(DomainException):
    status_code = 409
    default_message = "A imagem ainda não está pronta."


class AiImageQuotaExceededException(DomainException):
    status_code = 429
    default_message = "Limite diário de novas ilustrações atingido."
