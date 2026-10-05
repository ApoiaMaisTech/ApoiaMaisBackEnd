"""Aplica no MySQL os resultados publicados pelo go-worker.

O worker Go não acessa o banco: ele publica ai.image.started/generated/failed
e só a API altera o estado. Cada evento é processado uma única vez por
consumidor (tabela processed_event, na mesma transação da atualização).
Transições só avançam: pending -> processing -> completed | failed.
"""
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.events.ai_image import (
    AI_IMAGE_FAILED,
    AI_IMAGE_GENERATED,
    AI_IMAGE_STARTED,
    AiImageFailedV1,
    AiImageGeneratedV1,
    AiImageStartedV1,
)
from app.application.events.envelope import EventEnvelope
from app.domain.enums.ai_image import AiImageStatus
from app.infrastructure.database.models.ludic.ai_image_model import AiImageModel
from app.infrastructure.database.models.messaging.processed_event_model import ProcessedEventModel
from app.infrastructure.database.types import utcnow
from app.infrastructure.messaging.consumer import Handler, PermanentError

logger = logging.getLogger("apoiamais.ai_image_results")

CONSUMER_NAME = "apoiamais-api.ai-image-results"
QUEUE_NAME = "apoiamais-api.ai-image-results"

_OPEN = (AiImageStatus.PENDING, AiImageStatus.PROCESSING)


def _parse(model, envelope: EventEnvelope):
    try:
        payload = model.model_validate(envelope.payload)
    except ValidationError as exc:
        raise PermanentError(f"payload inválido para {envelope.event_type}") from exc
    if envelope.job_id is not None and envelope.job_id != payload.image_id:
        raise PermanentError("job_id diferente de image_id")
    return payload


class AiImageResultHandlers:
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    def handlers(self) -> dict[tuple[str, int], Handler]:
        return {
            (AI_IMAGE_STARTED, 1): self.on_started,
            (AI_IMAGE_GENERATED, 1): self.on_generated,
            (AI_IMAGE_FAILED, 1): self.on_failed,
        }

    async def _run(self, envelope: EventEnvelope, apply) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                key = (CONSUMER_NAME, str(envelope.event_id))
                if await session.get(ProcessedEventModel, key) is not None:
                    logger.info("evento duplicado ignorado")
                    return
                session.add(
                    ProcessedEventModel(
                        consumer=CONSUMER_NAME,
                        event_id=str(envelope.event_id),
                        event_type=envelope.event_type,
                    )
                )
                await apply(session)

    async def on_started(self, envelope: EventEnvelope) -> None:
        payload = _parse(AiImageStartedV1, envelope)

        async def apply(session: AsyncSession) -> None:
            await session.execute(
                update(AiImageModel)
                .where(AiImageModel.id == payload.image_id, AiImageModel.status == AiImageStatus.PENDING)
                .values(status=AiImageStatus.PROCESSING, updated_at=utcnow())
            )

        await self._run(envelope, apply)

    async def on_generated(self, envelope: EventEnvelope) -> None:
        payload = _parse(AiImageGeneratedV1, envelope)

        async def apply(session: AsyncSession) -> None:
            image = await self._get(session, payload.image_id)
            if image is None:
                return
            # o worker só pode ter gravado na chave que a API definiu
            if payload.storage_key != image.storage_key:
                raise PermanentError("storage_key diferente da esperada")
            now = utcnow()
            await session.execute(
                update(AiImageModel)
                .where(AiImageModel.id == payload.image_id, AiImageModel.status.in_(_OPEN))
                .values(
                    status=AiImageStatus.COMPLETED,
                    provider=payload.provider,
                    model=payload.model,
                    mime_type=payload.mime_type,
                    size_bytes=payload.size_bytes,
                    error_code=None,
                    error_message=None,
                    completed_at=now,
                    updated_at=now,
                )
            )

        await self._run(envelope, apply)

    async def on_failed(self, envelope: EventEnvelope) -> None:
        payload = _parse(AiImageFailedV1, envelope)

        async def apply(session: AsyncSession) -> None:
            if await self._get(session, payload.image_id) is None:
                return
            await session.execute(
                update(AiImageModel)
                .where(AiImageModel.id == payload.image_id, AiImageModel.status.in_(_OPEN))
                .values(
                    status=AiImageStatus.FAILED,
                    # libera a chave: um novo pedido (após o cooldown) pode tentar de novo
                    dedupe_key=None,
                    error_code=payload.error_code,
                    error_message=payload.error_message[:500] or None,
                    updated_at=utcnow(),
                )
            )

        await self._run(envelope, apply)

    @staticmethod
    async def _get(session: AsyncSession, image_id: UUID) -> AiImageModel | None:
        image = await session.get(AiImageModel, image_id)
        if image is None:
            logger.warning("resultado para imagem inexistente", extra={"image_id": str(image_id)})
        return image
