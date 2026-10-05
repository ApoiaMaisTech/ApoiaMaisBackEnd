"""Consumidor contra o RabbitMQ real: ack, retry, DLQ, alternate exchange.

Precisa de RABBITMQ_URL (o CI sobe o RabbitMQ como serviço). Cada teste usa
uma fila própria e a apaga no fim.
"""
import asyncio
import json
import os
from uuid import uuid4

import aio_pika
import pytest
import pytest_asyncio

from app.application.events.ai_image import AI_IMAGE_STARTED, AiImageStartedV1
from app.application.events.envelope import new_event
from app.infrastructure.messaging.consumer import EventConsumer, PermanentError
from app.infrastructure.messaging.publisher import RabbitPublisher
from app.infrastructure.messaging.topology import (
    RETRY_COUNT_HEADER,
    RETRY_DELAYS_MS,
    UNROUTED_QUEUE,
    dlq_name,
    retry_queue_name,
)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
pytestmark = pytest.mark.skipif(not RABBITMQ_URL, reason="RABBITMQ_URL não definido")


@pytest_asyncio.fixture
async def broker():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    queues: list[str] = []
    yield channel, queues
    for name in queues:
        for q in [name, dlq_name(name), *[retry_queue_name(name, d) for d in RETRY_DELAYS_MS]]:
            await channel.queue_delete(q)
    await connection.close()


async def _get(channel, queue_name, timeout=5.0):
    queue = await channel.get_queue(queue_name, ensure=False)
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        message = await queue.get(no_ack=True, fail=False)
        if message is not None:
            return message
        await asyncio.sleep(0.1)
    return None


def _event(event_type=AI_IMAGE_STARTED):
    image_id = uuid4()
    return new_event(event_type, 1, AiImageStartedV1(image_id=image_id), correlation_id="rmq-test", job_id=image_id)


async def _start_consumer(broker, handler, max_retries=3):
    channel, queues = broker
    queue_name = f"test.{uuid4().hex[:8]}"
    queues.append(queue_name)
    consumer = EventConsumer(RABBITMQ_URL, queue_name, {(AI_IMAGE_STARTED, 1): handler}, max_retries=max_retries)
    await consumer.start()
    publisher = RabbitPublisher(RABBITMQ_URL)
    await publisher.connect()
    return consumer, publisher, queue_name


async def _publish(publisher, envelope):
    await publisher.publish(
        envelope.to_json().encode(),
        routing_key=envelope.event_type,
        message_id=str(envelope.event_id),
        event_type=envelope.event_type,
        correlation_id=envelope.correlation_id,
    )


@pytest.mark.asyncio
async def test_evento_chega_ao_handler_e_recebe_ack(broker):
    received = asyncio.Queue()

    async def handler(envelope):
        await received.put(envelope)

    consumer, publisher, queue_name = await _start_consumer(broker, handler)
    try:
        event = _event()
        await _publish(publisher, event)

        got = await asyncio.wait_for(received.get(), timeout=5)
        assert got.event_id == event.event_id
        await asyncio.sleep(0.3)
        assert (await (await broker[0].get_queue(queue_name, ensure=False)).declare()).message_count == 0
    finally:
        await consumer.close()
        await publisher.close()


@pytest.mark.asyncio
async def test_erro_temporario_vai_para_a_fila_de_retry_com_contador(broker):
    async def handler(envelope):
        raise ConnectionError("banco fora")

    consumer, publisher, queue_name = await _start_consumer(broker, handler)
    try:
        await _publish(publisher, _event())

        message = await _get(broker[0], retry_queue_name(queue_name, RETRY_DELAYS_MS[0]))
        assert message is not None
        assert message.headers[RETRY_COUNT_HEADER] == 1
        assert "banco fora" in message.headers["x-last-error"]
    finally:
        await consumer.close()
        await publisher.close()


@pytest.mark.asyncio
async def test_tentativas_esgotadas_vao_para_a_dlq(broker):
    async def handler(envelope):
        raise ConnectionError("ainda fora")

    consumer, publisher, queue_name = await _start_consumer(broker, handler, max_retries=0)
    try:
        await _publish(publisher, _event())

        message = await _get(broker[0], dlq_name(queue_name))
        assert message is not None
        assert json.loads(message.body)["event_type"] == AI_IMAGE_STARTED
    finally:
        await consumer.close()
        await publisher.close()


@pytest.mark.asyncio
async def test_erro_permanente_vai_direto_para_a_dlq(broker):
    calls = 0

    async def handler(envelope):
        nonlocal calls
        calls += 1
        raise PermanentError("payload inválido")

    consumer, publisher, queue_name = await _start_consumer(broker, handler, max_retries=5)
    try:
        await _publish(publisher, _event())

        assert await _get(broker[0], dlq_name(queue_name)) is not None
        assert calls == 1
    finally:
        await consumer.close()
        await publisher.close()


@pytest.mark.asyncio
async def test_mensagem_malformada_vai_para_a_dlq(broker):
    async def handler(envelope):  # pragma: no cover - não deve ser chamado
        raise AssertionError

    consumer, publisher, queue_name = await _start_consumer(broker, handler)
    try:
        await publisher.publish(
            b"{nao e json", routing_key=AI_IMAGE_STARTED, message_id="x", event_type=AI_IMAGE_STARTED, correlation_id="c"
        )
        assert await _get(broker[0], dlq_name(queue_name)) is not None
    finally:
        await consumer.close()
        await publisher.close()


@pytest.mark.asyncio
async def test_evento_sem_consumidor_nao_se_perde(broker):
    channel, _ = broker
    publisher = RabbitPublisher(RABBITMQ_URL)
    await publisher.connect()
    routing_key = f"teste.semdono.{uuid4().hex[:8]}"
    try:
        unrouted = await channel.get_queue(UNROUTED_QUEUE, ensure=False)
        await unrouted.purge()
        await publisher.publish(
            b'{"x": 1}', routing_key=routing_key, message_id=routing_key, event_type=routing_key, correlation_id="c"
        )

        message = await _get(channel, UNROUTED_QUEUE)
        assert message is not None
        assert message.message_id == routing_key
    finally:
        await publisher.close()


@pytest.mark.asyncio
async def test_consumidor_volta_a_consumir_depois_de_perder_a_conexao(broker):
    # regressão: com connect_robust o consumidor não voltava depois de um restart do RabbitMQ
    channel, queues = broker
    received = asyncio.Queue()

    async def handler(envelope):
        await received.put(envelope)

    queue_name = f"test.{uuid4().hex[:8]}"
    queues.append(queue_name)
    consumer = EventConsumer(RABBITMQ_URL, queue_name, {(AI_IMAGE_STARTED, 1): handler})
    stop = asyncio.Event()
    task = asyncio.create_task(consumer.run(stop))
    publisher = RabbitPublisher(RABBITMQ_URL)
    await publisher.connect()

    async def wait_connected():
        for _ in range(100):
            if consumer.is_connected:
                return
            await asyncio.sleep(0.1)
        raise AssertionError("consumidor não conectou")

    try:
        await wait_connected()
        old_connection = consumer._connection
        await old_connection.close()  # simula a queda
        await asyncio.sleep(0.2)
        await wait_connected()
        assert consumer._connection is not old_connection

        event = _event()
        await _publish(publisher, event)
        got = await asyncio.wait_for(received.get(), timeout=5)
        assert got.event_id == event.event_id
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=10)
        await publisher.close()
