from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.ai_image import AiImage
from app.domain.enums.ai_image import AiImageStatus


class AiImageResponse(BaseModel):
    """O que o jogo precisa saber. Prompt, provedor e erros internos não saem daqui."""

    id: UUID
    status: AiImageStatus
    # caminho relativo na própria API (com autenticação); nunca URL do storage
    image_url: str | None = None
    # o jogo consulta de novo depois desse tempo enquanto não terminar
    retry_after_seconds: int | None = None

    @classmethod
    def from_entity(cls, image: AiImage) -> "AiImageResponse":
        done = image.status == AiImageStatus.COMPLETED
        open_ = image.status in (AiImageStatus.PENDING, AiImageStatus.PROCESSING)
        return cls(
            id=image.id,
            status=image.status,
            image_url=f"/api/ai-images/{image.id}/content" if done else None,
            retry_after_seconds=3 if open_ else None,
        )
