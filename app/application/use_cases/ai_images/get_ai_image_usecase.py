from uuid import UUID

from app.domain.entities.ai_image import AiImage
from app.domain.enums.ai_image import AiImageStatus
from app.domain.exceptions.ai_image import AiImageNotFoundException, AiImageNotReadyException
from app.domain.repositories.ai_image_repository import AiImageRepository
from app.infrastructure.storage import ObjectStorage


class GetAiImageUseCase:
    def __init__(self, repository: AiImageRepository):
        self.repository = repository

    async def execute(self, image_id: UUID) -> AiImage:
        image = await self.repository.get(image_id)
        if image is None:
            raise AiImageNotFoundException()
        return image


class GetAiImageContentUseCase:
    """Devolve os bytes da imagem pronta. A API serve o arquivo: o storage nunca é exposto."""

    def __init__(self, repository: AiImageRepository, storage: ObjectStorage):
        self.repository = repository
        self.storage = storage

    async def execute(self, image_id: UUID) -> tuple[bytes, str]:
        image = await self.repository.get(image_id)
        if image is None:
            raise AiImageNotFoundException()
        if image.status != AiImageStatus.COMPLETED:
            raise AiImageNotReadyException()

        content = await self.storage.get(image.storage_key)
        if content is None:
            raise AiImageNotFoundException()
        return content, image.mime_type or "image/png"
