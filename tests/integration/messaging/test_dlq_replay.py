"""Reprocessamento da DLQ contra o RabbitMQ real."""
import asyncio
import os
from uuid import uuid4

import aio_pika
import pytest
import pytest_asyncio

from app.application.events.ai_image import AI_IMAGE_STARTED, AiImageStartedV1
from app.application.events.envelope import new_event
from app.infrastructure.messaging.consumer import EventConsumer
from app.infrastructure.messaging.dlq import REPLAY_COUNT_HEADER, list_dlq, replay_dlq
from app.infrastructure.messaging.publisher import RabbitPublisher
from app.infrastructure.messaging.topology import RETRY_COUNT_HEADER, RETRY_DELAYS_MS, dlq_name, retry_queue_name

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
pytestmark = [
    pytest.mark.skipif(not RABBITMQ_URL, reason="RABBITMQ_URL não definido"),
    pytest.mark.asyncio,
]


class Switch:
    """Handler que falha até ser "consertado" e registra o que processou."""

    def __init__(self):
        self.broken = True
        self.seen: list = []

    async def __call__(self, envelope):
        if self.broken:
            raise ConnectionError("dependência fora")
        self.seen.append(envelope.event_id)


@pytest_asyncio.fixture
async def setup():
    queue_name = f"test.dlq.{uuid4().hex[:8]}"
    handler = Switch()
    consumer = EventConsumer(RABBITMQ_URL, queue_name, {(AI_IMAGE_STARTED, 1): handler}, max_retries=0)
    await consumer.start()
    publisher = RabbitPublisher(RABBITMQ_URL)
    await publisher.connect()
    yield queue_name, handler, publisher
    await consumer.close()
    await publisher.close()
    connection = await aio_pika.connect(RABBITMQ_URL)
    channel = await connection.channel()
    for q in [queue_name, dlq_name(queue_name), *[retry_queue_name(queue_name, d) for d in RETRY_DELAYS_MS]]:
        await channel.queue_delete(q)
    await connection.close()


async def _send(publisher, n=1, event_type=AI_IMAGE_STARTED):
    events = []
    for _ in range(n):
        image_id = uuid4()
        event = new_event(event_type, 1, AiImageStartedV1(image_id=image_id), correlation_id="dlq-test", job_id=image_id)
        await publisher.publish(
            event.to_json().encode(),
            routing_key=event.event_type,
            message_id=str(event.event_id),
            event_type=event.event_type,
            correlation_id=event.correlation_id,
        )
        events.append(event)
    return events


async def _wait_dlq(queue_name, expected, timeout=5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        total, _ = await list_dlq(RABBITMQ_URL, queue_name, limit=0)
        if total == expected:
            return total
        await asyncio.sleep(0.1)
    return (await list_dlq(RABBITMQ_URL, queue_name, limit=0))[0]


async def _wait_seen(handler, expected, timeout=5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline and len(handler.seen) < expected:
        await asyncio.sleep(0.1)


async def test_listar_nao_remove_e_mostra_o_erro(setup):
    queue_name, handler, publisher = setup
    events = await _send(publisher, 2)
    assert await _wait_dlq(queue_name, 2) == 2

    total, messages = await list_dlq(RABBITMQ_URL, queue_name)

    assert total == 2
    assert {m.message_id for m in messages} == {str(e.event_id) for e in events}
    assert all("dependência fora" in m.last_error for m in messages)
    assert (await list_dlq(RABBITMQ_URL, queue_name, limit=0))[0] == 2


async def test_reprocessa_depois_de_corrigir_a_causa(setup):
    queue_name, handler, publisher = setup
    events = await _send(publisher, 3)
    assert await _wait_dlq(queue_name, 3) == 3

    handler.broken = False
    result = await replay_dlq(RABBITMQ_URL, queue_name)

    assert result.replayed == 3 and result.failed == 0
    await _wait_seen(handler, 3)
    assert set(handler.seen) == {e.event_id for e in events}
    assert await _wait_dlq(queue_name, 0) == 0


async def test_falha_de_novo_volta_para_a_dlq_sem_loop(setup):
    queue_name, handler, publisher = setup
    await _send(publisher, 2)
    assert await _wait_dlq(queue_name, 2) == 2

    # ainda quebrado: as mensagens voltam para a DLQ, mas a execução termina
    result = await asyncio.wait_for(replay_dlq(RABBITMQ_URL, queue_name), timeout=10)

    assert result.replayed == 2
    assert await _wait_dlq(queue_name, 2) == 2
    _, messages = await list_dlq(RABBITMQ_URL, queue_name)
    assert all(m.replay_count == 1 for m in messages)


async def test_limite_de_reprocessamentos_mantem_na_dlq(setup):
    queue_name, handler, publisher = setup
    await _send(publisher, 1)
    assert await _wait_dlq(queue_name, 1) == 1

    for _ in range(2):
        await replay_dlq(RABBITMQ_URL, queue_name, max_replays=2)
        assert await _wait_dlq(queue_name, 1) == 1

    handler.broken = False
    result = await replay_dlq(RABBITMQ_URL, queue_name, max_replays=2)

    assert result.replayed == 0 and result.kept == 1
    assert await _wait_dlq(queue_name, 1) == 1
    assert handler.seen == []


async def test_limite_e_filtro_por_tipo(setup):
    queue_name, handler, publisher = setup
    await _send(publisher, 3)
    assert await _wait_dlq(queue_name, 3) == 3
    handler.broken = False

    assert (await replay_dlq(RABBITMQ_URL, queue_name, event_type="ai.image.generated")).replayed == 0
    assert await _wait_dlq(queue_name, 3) == 3

    result = await replay_dlq(RABBITMQ_URL, queue_name, limit=1)
    assert result.replayed == 1
    assert await _wait_dlq(queue_name, 2) == 2


async def test_mensagem_reprocessada_volta_com_contador_zerado(setup):
    from app.infrastructure.messaging.topology import build_message

    queue_name, handler, publisher = setup
    image_id = uuid4()
    event = new_event(AI_IMAGE_STARTED, 1, AiImageStartedV1(image_id=image_id), correlation_id="dlq-test", job_id=image_id)

    # mensagem que esgotou as tentativas: contador alto e histórico do broker
    connection = await aio_pika.connect(RABBITMQ_URL)
    channel = await connection.channel(publisher_confirms=True)
    await channel.default_exchange.publish(
        build_message(
            event.to_json().encode(),
            message_id=str(event.event_id),
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            headers={RETRY_COUNT_HEADER: 3, "x-last-error": "ConnectionError: antigo", "x-death": [{"count": 3}]},
        ),
        routing_key=dlq_name(queue_name),
    )
    assert await _wait_dlq(queue_name, 1) == 1

    # o consumidor ainda está quebrado: a reentrega falha uma vez e volta para a DLQ
    await replay_dlq(RABBITMQ_URL, queue_name)
    assert await _wait_dlq(queue_name, 1) == 1
    message = await (await channel.get_queue(dlq_name(queue_name), ensure=False)).get(no_ack=True)
    await connection.close()

    # recomeçou do zero (com max_retries=3 teria passado pelo retry de novo), sem x-death antigo
    assert message.headers[RETRY_COUNT_HEADER] == 0
    assert message.headers[REPLAY_COUNT_HEADER] == 1
    assert message.headers["x-dlq-last-error"] == "ConnectionError: antigo"
    assert "dependência fora" in message.headers["x-last-error"]
    assert "x-death" not in message.headers or message.headers["x-death"] != [{"count": 3}]
