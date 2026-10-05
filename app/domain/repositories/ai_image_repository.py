from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.application.events.envelope import EventEnvelope
from app.domain.entities.ai_image import AiImage, StageTheme


class AiImageRepository(ABC):
    @abstractmethod
    async def get(self, image_id: UUID) -> AiImage | None: ...

    @abstractmethod
    async def get_stage_theme(self, stage_id: UUID) -> StageTheme | None: ...

    @abstractmethod
    async def get_by_dedupe_key(self, dedupe_key: str) -> AiImage | None: ...

    @abstractmethod
    async def get_recent_failure(
        self, stage_id: UUID, prompt_hash: str, since: datetime
    ) -> AiImage | None: ...

    @abstractmethod
    async def count_requested_by_since(self, user_id: UUID, since: datetime) -> int: ...

    @abstractmethod
    async def create_with_event(self, image: AiImage, event: EventEnvelope) -> AiImage:
        """Grava a imagem e o evento no outbox na mesma transação.

        Se outra requisição criou a mesma imagem antes (dedupe_key), devolve a existente
        e não grava evento.
        """
