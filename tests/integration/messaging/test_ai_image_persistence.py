"""Repositório, outbox e handlers de resultado contra o MySQL real."""
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.application.events.ai_image import (
    AI_IMAGE_FAILED,
    AI_IMAGE_GENERATED,
    AI_IMAGE_STARTED,
    AiImageFailedV1,
    AiImageGeneratedV1,
    AiImageStartedV1,
)
from app.application.events.envelope import EventEnvelope, new_event
from app.application.use_cases.ai_images.request_stage_illustration_usecase import (
    RequestStageIllustrationUseCase,
)
from app.domain.entities.user import User
from app.domain.enums.ai_image import AiImageStatus
from app.domain.enums.user import UserRole
from app.infrastructure.database.models.messaging.outbox_event_model import OutboxEventModel
from app.infrastructure.database.models.messaging.processed_event_model import ProcessedEventModel
from app.infrastructure.database.repositories.sql_ai_image_repository import SqlAiImageRepository
from app.infrastructure.database.repositories.sql_user_repository import SqlUserRepository
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.messaging.consumer import PermanentError
from app.infrastructure.messaging.handlers.ai_image_results import AiImageResultHandlers
from app.infrastructure.messaging.outbox import OutboxRelay


async def _request(stage_id: UUID, user_id: UUID):
    async with AsyncSessionLocal() as session:
        use_case = RequestStageIllustrationUseCase(
            SqlAiImageRepository(session), daily_quota_per_user=100, failure_cooldown_minutes=10
        )
        return await use_case.execute(stage_id, user_id, "corr-test")


async def _get(image_id: UUID):
    async with AsyncSessionLocal() as session:
        return await SqlAiImageRepository(session).get(image_id)


def _result(event_type: str, payload) -> EventEnvelope:
    return new_event(event_type, 1, payload, correlation_id="corr-test", job_id=payload.image_id)


def _generated(image) -> EventEnvelope:
    return _result(
        AI_IMAGE_GENERATED,
        AiImageGeneratedV1(
            image_id=image.id,
            storage_key=image.storage_key,
            mime_type="image/png",
            size_bytes=1234,
            provider="fake",
            model="placeholder-v1",
        ),
    )


class FakePublisher:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.published: list[dict] = []

    async def publish(self, body, *, routing_key, message_id, event_type, correlation_id):
        if self.fail:
            raise ConnectionError("broker fora")
        self.published.append(
            {"body": json.loads(body), "routing_key": routing_key, "message_id": message_id}
        )


@pytest.mark.asyncio
async def test_medico_e_administrador_podem_ser_gravados(db_session):
    # a migration inicial só aceitava STUDENT/TEACHER no MySQL
    repository = SqlUserRepository(db_session)
    for role in (UserRole.DOCTOR, UserRole.ADMIN):
        user = await repository.create(
            User(id=uuid4(), name="Perfil", email=f"{uuid4().hex}@example.com", password_hash="x", role=role)
        )
        assert (await repository.get_by_id(user.id)).role == role
        await repository.delete(user.id)


@pytest.mark.asyncio
async def test_pedido_grava_imagem_e_evento_na_mesma_transacao(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)

    assert image.status == AiImageStatus.PENDING
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(OutboxEventModel))).scalars().all()
    [row] = rows
    body = json.loads(row.body)
    assert row.routing_key == "ai.image.requested"
    assert body["job_id"] == str(image.id)
    assert body["payload"]["storage_key"] == image.storage_key
    assert row.published_at is None


@pytest.mark.asyncio
async def test_mesma_fase_reaproveita_imagem_no_banco(stage_id, user_id, clean_outbox):
    first = await _request(stage_id, user_id)
    second = await _request(stage_id, user_id)

    assert first.id == second.id
    async with AsyncSessionLocal() as session:
        assert len((await session.execute(select(OutboxEventModel))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_relay_publica_e_marca_o_outbox(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)
    publisher = FakePublisher()

    assert await OutboxRelay(AsyncSessionLocal, publisher).run_once() == 1
    assert await OutboxRelay(AsyncSessionLocal, publisher).run_once() == 0

    [message] = publisher.published
    assert message["routing_key"] == "ai.image.requested"
    assert message["body"]["payload"]["image_id"] == str(image.id)


@pytest.mark.asyncio
async def test_relay_com_broker_fora_mantem_o_evento_e_agenda_nova_tentativa(stage_id, user_id, clean_outbox):
    await _request(stage_id, user_id)

    assert await OutboxRelay(AsyncSessionLocal, FakePublisher(fail=True)).run_once() == 0

    async with AsyncSessionLocal() as session:
        [row] = (await session.execute(select(OutboxEventModel))).scalars().all()
    assert row.published_at is None
    assert row.attempts == 1
    assert "broker fora" in row.last_error
    assert row.next_attempt_at > datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_resultados_avancam_o_status(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)
    handlers = AiImageResultHandlers(AsyncSessionLocal)

    await handlers.on_started(_result(AI_IMAGE_STARTED, AiImageStartedV1(image_id=image.id)))
    assert (await _get(image.id)).status == AiImageStatus.PROCESSING

    await handlers.on_generated(_generated(image))
    done = await _get(image.id)
    assert done.status == AiImageStatus.COMPLETED
    assert done.provider == "fake" and done.size_bytes == 1234
    assert done.completed_at is not None

    # started atrasado não faz voltar
    await handlers.on_started(_result(AI_IMAGE_STARTED, AiImageStartedV1(image_id=image.id)))
    assert (await _get(image.id)).status == AiImageStatus.COMPLETED


@pytest.mark.asyncio
async def test_evento_duplicado_e_processado_uma_vez(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)
    handlers = AiImageResultHandlers(AsyncSessionLocal)
    event = _generated(image)

    await handlers.on_generated(event)
    await handlers.on_generated(event)

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(ProcessedEventModel).where(ProcessedEventModel.event_id == str(event.event_id))
            )
        ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_falha_libera_a_fase_para_nova_tentativa_depois(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)
    handlers = AiImageResultHandlers(AsyncSessionLocal)

    await handlers.on_failed(
        _result(AI_IMAGE_FAILED, AiImageFailedV1(image_id=image.id, error_code="provider_unavailable"))
    )

    failed = await _get(image.id)
    assert failed.status == AiImageStatus.FAILED
    assert failed.dedupe_key is None
    assert failed.error_code == "provider_unavailable"
    # dentro do cooldown, o mesmo pedido devolve a falha sem criar job
    assert (await _request(stage_id, user_id)).id == image.id


@pytest.mark.asyncio
async def test_storage_key_diferente_da_esperada_e_rejeitada(stage_id, user_id, clean_outbox):
    image = await _request(stage_id, user_id)
    handlers = AiImageResultHandlers(AsyncSessionLocal)
    other = uuid4()
    event = _result(
        AI_IMAGE_GENERATED,
        AiImageGeneratedV1(
            image_id=image.id,
            storage_key=f"ai-images/{other.hex}.png",
            mime_type="image/png",
            size_bytes=10,
            provider="fake",
            model="m",
        ),
    )

    with pytest.raises(PermanentError):
        await handlers.on_generated(event)
    # nada foi gravado (nem a marca de processado): o evento vai para a DLQ
    assert (await _get(image.id)).status == AiImageStatus.PENDING


@pytest.mark.asyncio
async def test_resultado_para_imagem_inexistente_e_ignorado():
    handlers = AiImageResultHandlers(AsyncSessionLocal)

    await handlers.on_started(_result(AI_IMAGE_STARTED, AiImageStartedV1(image_id=uuid4())))
