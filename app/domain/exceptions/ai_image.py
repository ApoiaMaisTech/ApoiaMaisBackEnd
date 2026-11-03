from .base import DomainException


class StageNotFoundException(DomainException):
    status_code = 404
    code = "STAGE_NOT_FOUND"
    default_message = "Fase não encontrada."


class AiImageNotFoundException(DomainException):
    status_code = 404
    code = "AI_IMAGE_NOT_FOUND"
    default_message = "Imagem não encontrada."


class AiImageNotReadyException(DomainException):
    status_code = 409
    code = "AI_IMAGE_NOT_READY"
    default_message = "A imagem ainda não está pronta."


class AiImageQuotaExceededException(DomainException):
    status_code = 429
    code = "AI_IMAGE_QUOTA_EXCEEDED"
    default_message = "Limite diário de novas ilustrações atingido."
