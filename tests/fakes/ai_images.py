from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.application.events.envelope import EventEnvelope
from app.domain.entities.ai_image import AiImage, StageTheme
from app.domain.enums.ai_image import AiImageStatus
from app.domain.repositories.ai_image_repository import AiImageRepository
from app.infrastructure.database.types import utcnow


class InMemoryAiImageRepository(AiImageRepository):
    """Repositório falso: exercita use cases e rotas reais sem MySQL."""

    def __init__(self):
        self.images: dict[UUID, AiImage] = {}
        self.stages: dict[UUID, StageTheme] = {}
        self.events: list[EventEnvelope] = []
        self.updated_at: dict[UUID, datetime] = {}

    async def get(self, image_id: UUID) -> AiImage | None:
        return self.images.get(image_id)

    async def get_stage_theme(self, stage_id: UUID) -> StageTheme | None:
        return self.stages.get(stage_id)

    async def get_by_dedupe_key(self, dedupe_key: str) -> AiImage | None:
        return next((i for i in self.images.values() if i.dedupe_key == dedupe_key), None)

    async def get_recent_failure(self, stage_id, prompt_hash, since) -> AiImage | None:
        failures = [
            i
            for i in self.images.values()
            if i.stage_id == stage_id
            and i.prompt_hash == prompt_hash
            and i.status == AiImageStatus.FAILED
            and self.updated_at.get(i.id, utcnow()) >= since
        ]
        return failures[-1] if failures else None

    async def count_requested_by_since(self, user_id: UUID, since: datetime) -> int:
        return sum(
            1
            for i in self.images.values()
            if i.requested_by_user_id == user_id and (i.created_at or utcnow()) >= since
        )

    async def create_with_event(self, image: AiImage, event: EventEnvelope) -> AiImage:
        existing = await self.get_by_dedupe_key(image.dedupe_key or "")
        if existing is not None:
            return existing
        stored = replace(image, created_at=utcnow())
        self.images[image.id] = stored
        self.events.append(event)
        return stored

    # atalhos para os testes
    def set_status(self, image_id: UUID, status: AiImageStatus, **changes) -> None:
        image = self.images[image_id]
        if status == AiImageStatus.FAILED:
            changes.setdefault("dedupe_key", None)
        self.images[image_id] = replace(image, status=status, **changes)
        self.updated_at[image_id] = utcnow()


class InMemoryStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.objects.get(key)
