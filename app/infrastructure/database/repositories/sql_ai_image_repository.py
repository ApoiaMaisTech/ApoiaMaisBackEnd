from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# garante que stage/world/user estejam no metadata (FKs do ai_image)
import app.infrastructure.database.models  # noqa: F401
from app.application.events.envelope import EventEnvelope
from app.domain.entities.ai_image import AiImage, StageTheme
from app.domain.enums.ai_image import AiImageStatus
from app.domain.repositories.ai_image_repository import AiImageRepository
from app.infrastructure.database.models.ludic.ai_image_model import AiImageModel
from app.infrastructure.database.models.ludic.stage_model import StageModel
from app.infrastructure.database.models.ludic.world_model import WorldModel
from app.infrastructure.messaging.outbox import add_to_outbox


def to_entity(model: AiImageModel) -> AiImage:
    return AiImage(
        id=model.id,
        stage_id=model.stage_id,
        requested_by_user_id=model.requested_by_user_id,
        dedupe_key=model.dedupe_key,
        prompt=model.prompt,
        prompt_hash=model.prompt_hash,
        status=model.status,
        storage_key=model.storage_key,
        provider=model.provider,
        model=model.model,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        error_code=model.error_code,
        correlation_id=model.correlation_id,
        created_at=model.created_at,
        completed_at=model.completed_at,
    )


class SqlAiImageRepository(AiImageRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get(self, image_id: UUID) -> AiImage | None:
        model = await self.db_session.get(AiImageModel, image_id)
        return to_entity(model) if model else None

    async def get_stage_theme(self, stage_id: UUID) -> StageTheme | None:
        stmt = (
            select(StageModel.name, WorldModel.name)
            .join(WorldModel, WorldModel.id == StageModel.world_id)
            .where(StageModel.id == stage_id)
        )
        row = (await self.db_session.execute(stmt)).first()
        if row is None:
            return None
        return StageTheme(stage_name=row[0], world_name=row[1])

    async def get_by_dedupe_key(self, dedupe_key: str) -> AiImage | None:
        stmt = select(AiImageModel).where(AiImageModel.dedupe_key == dedupe_key)
        model = (await self.db_session.execute(stmt)).scalar_one_or_none()
        return to_entity(model) if model else None

    async def get_recent_failure(
        self, stage_id: UUID, prompt_hash: str, since: datetime
    ) -> AiImage | None:
        stmt = (
            select(AiImageModel)
            .where(
                AiImageModel.stage_id == stage_id,
                AiImageModel.prompt_hash == prompt_hash,
                AiImageModel.status == AiImageStatus.FAILED,
                AiImageModel.updated_at >= since,
            )
            .order_by(AiImageModel.updated_at.desc())
            .limit(1)
        )
        model = (await self.db_session.execute(stmt)).scalar_one_or_none()
        return to_entity(model) if model else None

    async def count_requested_by_since(self, user_id: UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(AiImageModel).where(
            AiImageModel.requested_by_user_id == user_id,
            AiImageModel.created_at >= since,
        )
        return int((await self.db_session.execute(stmt)).scalar_one())

    async def create_with_event(self, image: AiImage, event: EventEnvelope) -> AiImage:
        model = AiImageModel(
            id=image.id,
            stage_id=image.stage_id,
            requested_by_user_id=image.requested_by_user_id,
            dedupe_key=image.dedupe_key,
            prompt=image.prompt,
            prompt_hash=image.prompt_hash,
            status=image.status,
            storage_key=image.storage_key,
            correlation_id=image.correlation_id,
        )
        self.db_session.add(model)
        add_to_outbox(self.db_session, event)
        try:
            await self.db_session.commit()
        except IntegrityError:
            # outra criança abriu a mesma fase no mesmo instante: usa a imagem dela
            await self.db_session.rollback()
            existing = await self.get_by_dedupe_key(image.dedupe_key or "")
            if existing is None:
                raise
            return existing
        await self.db_session.refresh(model)
        return to_entity(model)
