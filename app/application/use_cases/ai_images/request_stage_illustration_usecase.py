from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.application.events.ai_image import AI_IMAGE_REQUESTED, AiImageRequestedV1, storage_key_for
from app.application.events.envelope import new_event
from app.domain.entities.ai_image import AiImage
from app.domain.enums.ai_image import AiImageStatus
from app.domain.exceptions.ai_image import AiImageQuotaExceededException, StageNotFoundException
from app.domain.repositories.ai_image_repository import AiImageRepository
from app.domain.services.illustration_prompt import build_prompt, prompt_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RequestStageIllustrationUseCase:
    """O jogo pede a ilustração da fase que a criança está jogando.

    1. imagem da fase já pronta ou em geração -> devolve a mesma (sem custo)
    2. falhou há pouco -> devolve a falha (o jogo mostra a ilustração padrão),
       sem martelar o provedor
    3. senão, respeitando a cota diária do usuário, cria o job e o evento
       ai.image.requested no outbox, na mesma transação
    """

    def __init__(
        self,
        repository: AiImageRepository,
        daily_quota_per_user: int,
        failure_cooldown_minutes: int,
    ):
        self.repository = repository
        self.daily_quota_per_user = daily_quota_per_user
        self.failure_cooldown = timedelta(minutes=failure_cooldown_minutes)

    async def execute(self, stage_id: UUID, user_id: UUID, correlation_id: str) -> AiImage:
        theme = await self.repository.get_stage_theme(stage_id)
        if theme is None:
            raise StageNotFoundException()

        prompt = build_prompt(theme)
        hashed = prompt_hash(prompt)
        dedupe_key = f"{stage_id.hex}:{hashed[:32]}"

        existing = await self.repository.get_by_dedupe_key(dedupe_key)
        if existing is not None:
            return existing

        now = _utcnow()
        recent_failure = await self.repository.get_recent_failure(
            stage_id, hashed, now - self.failure_cooldown
        )
        if recent_failure is not None:
            return recent_failure

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        used = await self.repository.count_requested_by_since(user_id, start_of_day)
        if used >= self.daily_quota_per_user:
            raise AiImageQuotaExceededException()

        image_id = uuid4()
        image = AiImage(
            id=image_id,
            stage_id=stage_id,
            requested_by_user_id=user_id,
            dedupe_key=dedupe_key,
            prompt=prompt,
            prompt_hash=hashed,
            status=AiImageStatus.PENDING,
            storage_key=storage_key_for(image_id),
            correlation_id=correlation_id,
        )
        event = new_event(
            AI_IMAGE_REQUESTED,
            1,
            AiImageRequestedV1(image_id=image_id, prompt=prompt, storage_key=image.storage_key),
            correlation_id=correlation_id,
            job_id=image_id,
        )
        return await self.repository.create_with_event(image, event)
