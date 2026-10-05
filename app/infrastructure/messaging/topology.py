"""Topologia do RabbitMQ (espelhada em workers/go-worker/internal/broker/topology.go).

- apoiamais.events (topic): todos os eventos; routing key = event_type.
  Mensagem sem fila de destino vai para apoiamais.unrouted (alternate exchange),
  então nada se perde se um consumidor ainda não declarou a fila dele.
- Cada consumidor é dono das suas filas:
    <fila>                 quorum, com DLX e x-delivery-limit (proteção contra crash em loop)
    <fila>.retry.<ms>      TTL; ao expirar volta para <fila> pelo default exchange
    <fila>.dlq             mensagens que esgotaram as tentativas ou são inválidas

Os argumentos precisam ser idênticos em Python e Go: o RabbitMQ recusa
(PRECONDITION_FAILED) redeclarar fila/exchange com argumentos diferentes.
"""
import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

EVENTS_EXCHANGE = "apoiamais.events"
RETRY_EXCHANGE = "apoiamais.retry"
DLX_EXCHANGE = "apoiamais.dlx"
UNROUTED_EXCHANGE = "apoiamais.unrouted"
UNROUTED_QUEUE = "apoiamais.unrouted"

RETRY_DELAYS_MS = (10_000, 60_000, 300_000)
DELIVERY_LIMIT = 10

RETRY_COUNT_HEADER = "x-retry-count"
ERROR_HEADER = "x-last-error"


def retry_queue_name(queue: str, delay_ms: int) -> str:
    return f"{queue}.retry.{delay_ms}"


def dlq_name(queue: str) -> str:
    return f"{queue}.dlq"


def retry_delay_for(attempt: int) -> int:
    # attempt começa em 1; depois da última faixa, repete a maior
    return RETRY_DELAYS_MS[min(attempt, len(RETRY_DELAYS_MS)) - 1]


async def declare_exchanges(channel: AbstractChannel) -> dict[str, AbstractExchange]:
    unrouted = await channel.declare_exchange(UNROUTED_EXCHANGE, ExchangeType.FANOUT, durable=True)
    unrouted_queue = await channel.declare_queue(
        UNROUTED_QUEUE, durable=True, arguments={"x-queue-type": "quorum"}
    )
    await unrouted_queue.bind(unrouted)

    events = await channel.declare_exchange(
        EVENTS_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
        arguments={"alternate-exchange": UNROUTED_EXCHANGE},
    )
    retry = await channel.declare_exchange(RETRY_EXCHANGE, ExchangeType.DIRECT, durable=True)
    dlx = await channel.declare_exchange(DLX_EXCHANGE, ExchangeType.DIRECT, durable=True)
    return {"events": events, "retry": retry, "dlx": dlx}


async def declare_consumer_queue(
    channel: AbstractChannel, queue_name: str, bindings: list[str]
) -> AbstractQueue:
    exchanges = await declare_exchanges(channel)

    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": DLX_EXCHANGE,
            "x-dead-letter-routing-key": queue_name,
            "x-delivery-limit": DELIVERY_LIMIT,
        },
    )
    for routing_key in bindings:
        await queue.bind(exchanges["events"], routing_key=routing_key)

    for delay in RETRY_DELAYS_MS:
        name = retry_queue_name(queue_name, delay)
        retry_queue = await channel.declare_queue(
            name,
            durable=True,
            arguments={
                "x-message-ttl": delay,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": queue_name,
            },
        )
        await retry_queue.bind(exchanges["retry"], routing_key=name)

    dlq = await channel.declare_queue(
        dlq_name(queue_name), durable=True, arguments={"x-queue-type": "quorum"}
    )
    await dlq.bind(exchanges["dlx"], routing_key=queue_name)
    return queue


def build_message(
    body: bytes,
    *,
    message_id: str,
    event_type: str,
    correlation_id: str,
    headers: dict | None = None,
) -> aio_pika.Message:
    return aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=message_id,
        type=event_type,
        correlation_id=correlation_id,
        headers=headers or {},
    )
