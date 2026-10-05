from datetime import timedelta
from uuid import uuid4

import pytest

from app.application.events.ai_image import AI_IMAGE_REQUESTED, AiImageRequestedV1
from app.application.use_cases.ai_images.request_stage_illustration_usecase import (
    RequestStageIllustrationUseCase,
)
from app.domain.entities.ai_image import StageTheme
from app.domain.enums.ai_image import AiImageStatus
from app.domain.exceptions.ai_image import AiImageQuotaExceededException, StageNotFoundException

from app.infrastructure.database.types import utcnow

from tests.fakes.ai_images import InMemoryAiImageRepository


def _setup(quota=5):
    repo = InMemoryAiImageRepository()
    stage_id = uuid4()
    repo.stages[stage_id] = StageTheme(stage_name="Vogais", world_name="Floresta")
    use_case = RequestStageIllustrationUseCase(repo, daily_quota_per_user=quota, failure_cooldown_minutes=10)
    return repo, stage_id, use_case


@pytest.mark.asyncio
async def test_primeiro_pedido_cria_job_pendente_e_evento():
    repo, stage_id, use_case = _setup()
    user_id = uuid4()

    image = await use_case.execute(stage_id, user_id, "corr-1")

    assert image.status == AiImageStatus.PENDING
    assert image.requested_by_user_id == user_id
    assert image.storage_key == f"ai-images/{image.id.hex}.png"
    [event] = repo.events
    assert event.event_type == AI_IMAGE_REQUESTED
    assert event.job_id == image.id
    assert event.correlation_id == "corr-1"
    payload = AiImageRequestedV1.model_validate(event.payload)
    assert payload.storage_key == image.storage_key
    # nada do usuário vai para o provedor
    assert str(user_id) not in event.to_json()


@pytest.mark.asyncio
async def test_segunda_crianca_na_mesma_fase_reaproveita_a_imagem():
    repo, stage_id, use_case = _setup()

    first = await use_case.execute(stage_id, uuid4(), "c1")
    second = await use_case.execute(stage_id, uuid4(), "c2")

    assert second.id == first.id
    assert len(repo.events) == 1


@pytest.mark.asyncio
async def test_fase_inexistente():
    _, _, use_case = _setup()

    with pytest.raises(StageNotFoundException):
        await use_case.execute(uuid4(), uuid4(), "c")


@pytest.mark.asyncio
async def test_falha_recente_e_devolvida_sem_novo_job():
    repo, stage_id, use_case = _setup()
    first = await use_case.execute(stage_id, uuid4(), "c1")
    repo.set_status(first.id, AiImageStatus.FAILED)

    again = await use_case.execute(stage_id, uuid4(), "c2")

    assert again.id == first.id
    assert again.status == AiImageStatus.FAILED
    assert len(repo.events) == 1


@pytest.mark.asyncio
async def test_depois_do_cooldown_cria_novo_job():
    repo, stage_id, use_case = _setup()
    first = await use_case.execute(stage_id, uuid4(), "c1")
    repo.set_status(first.id, AiImageStatus.FAILED)
    repo.updated_at[first.id] = utcnow() - timedelta(hours=1)  # falhou há 1h (cooldown de 10 min)

    again = await use_case.execute(stage_id, uuid4(), "c2")

    assert again.id != first.id
    assert again.status == AiImageStatus.PENDING
    assert len(repo.events) == 2


@pytest.mark.asyncio
async def test_cota_diaria_por_usuario_vale_so_para_novos_jobs():
    repo, _, use_case = _setup(quota=2)
    user_id = uuid4()
    stages = [uuid4() for _ in range(3)]
    for s in stages:
        repo.stages[s] = StageTheme(stage_name=f"Fase {s.hex[:4]}", world_name="Mundo")

    await use_case.execute(stages[0], user_id, "c")
    await use_case.execute(stages[1], user_id, "c")
    with pytest.raises(AiImageQuotaExceededException):
        await use_case.execute(stages[2], user_id, "c")

    # imagem já existente não conta como novo job
    cached = await use_case.execute(stages[0], user_id, "c")
    assert cached.status == AiImageStatus.PENDING
