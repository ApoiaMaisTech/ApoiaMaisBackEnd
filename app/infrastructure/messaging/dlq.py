"""Inspeção e reprocessamento da DLQ (recuperação depois de corrigir a causa da falha).

Vale para qualquer fila da topologia (Python ou Go): a DLQ de `Q` é `Q.dlq` e o
reprocessamento devolve a mensagem para `Q` pelo default exchange, com o
contador de tentativas zerado. É seguro reprocessar porque todo consumidor é
idempotente (event_id).

Garantias:
- a mensagem só sai da DLQ (ack) depois que o broker confirmou a cópia em `Q`
  (publisher confirms); se a publicação falhar, ela volta para a DLQ (nack com requeue);
- cada execução processa no máximo as mensagens que estavam na DLQ no início:
  uma mensagem que falhar de novo e voltar para a DLQ não entra em loop;
- `x-replay-count` conta quantas vezes a mensagem já foi reprocessada; acima de
  `max_replays` ela fica na DLQ (vá investigar em vez de insistir).
"""
import logging
from dataclasses import dataclass, field

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from app.infrastructure.messaging.topology import ERROR_HEADER, RETRY_COUNT_HEADER, build_message, dlq_name

logger = logging.getLogger("apoiamais.dlq")

REPLAY_COUNT_HEADER = "x-replay-count"
DLQ_ERROR_HEADER = "x-dlq-last-error"
# cabeçalhos do RabbitMQ que descrevem a passagem anterior; uma reentrega limpa não os leva
_BROKER_HEADERS = ("x-death", "x-first-death-exchange", "x-first-death-queue", "x-first-death-reason",
                   "x-last-death-exchange", "x-last-death-queue", "x-last-death-reason", "x-delivery-count")


@dataclass
class DlqMessage:
    message_id: str
    event_type: str
    correlation_id: str
    retry_count: int
    replay_count: int
    last_error: str


@dataclass
class ReplayResult:
    replayed: int = 0
    kept: int = 0
    failed: int = 0
    kept_ids: list[str] = field(default_factory=list)


def _int_header(message: AbstractIncomingMessage, name: str) -> int:
    try:
        return max(0, int((message.headers or {}).get(name, 0) or 0))
    except (TypeError, ValueError):
        return 0


def _describe(message: AbstractIncomingMessage) -> DlqMessage:
    headers = message.headers or {}
    return DlqMessage(
        message_id=message.message_id or "",
        event_type=message.type or "",
        correlation_id=message.correlation_id or "",
        retry_count=_int_header(message, RETRY_COUNT_HEADER),
        replay_count=_int_header(message, REPLAY_COUNT_HEADER),
        last_error=str(headers.get(ERROR_HEADER, "")),
    )


async def _message_count(channel: AbstractChannel, queue_name: str) -> int:
    queue = await channel.declare_queue(queue_name, passive=True)
    return queue.declaration_result.message_count or 0


async def list_dlq(url: str, queue_name: str, limit: int = 20) -> tuple[int, list[DlqMessage]]:
    """Mostra até `limit` mensagens da DLQ sem removê-las."""
    connection = await aio_pika.connect(url)
    try:
        channel = await connection.channel()
        dlq = dlq_name(queue_name)
        total = await _message_count(channel, dlq)
        queue = await channel.get_queue(dlq, ensure=False)
        held: list[AbstractIncomingMessage] = []
        for _ in range(min(limit, total)):
            message = await queue.get(no_ack=False, fail=False)
            if message is None:
                break
            held.append(message)
        described = [_describe(m) for m in held]
        # segura todas até o fim (senão a mesma voltaria no próximo get) e devolve
        for message in held:
            await message.nack(requeue=True)
        return total, described
    finally:
        await connection.close()


async def replay_dlq(
    url: str,
    queue_name: str,
    limit: int | None = None,
    event_type: str | None = None,
    max_replays: int = 3,
) -> ReplayResult:
    """Devolve mensagens de `<fila>.dlq` para `<fila>`. Ver as garantias no topo do módulo."""
    result = ReplayResult()
    connection = await aio_pika.connect(url)
    try:
        channel = await connection.channel(publisher_confirms=True)
        dlq = dlq_name(queue_name)
        # a fila de destino precisa existir (o consumidor a declara); passive falha se não existir
        await channel.declare_queue(queue_name, passive=True)
        pending = await _message_count(channel, dlq)
        if limit is not None:
            pending = min(pending, limit)
        source = await channel.get_queue(dlq, ensure=False)

        for _ in range(pending):
            message = await source.get(no_ack=False, fail=False)
            if message is None:
                break
            info = _describe(message)
            headers = dict(message.headers or {})

            keep = (event_type is not None and info.event_type != event_type) or info.replay_count >= max_replays
            if keep:
                # volta para o fim da DLQ (sem reordenar a execução atual)
                target, routing_key = dlq, dlq
                result.kept += 1
                result.kept_ids.append(info.message_id)
            else:
                for name in _BROKER_HEADERS:
                    headers.pop(name, None)
                headers[RETRY_COUNT_HEADER] = 0
                headers[REPLAY_COUNT_HEADER] = info.replay_count + 1
                if ERROR_HEADER in headers:
                    headers[DLQ_ERROR_HEADER] = headers.pop(ERROR_HEADER)
                target, routing_key = queue_name, queue_name

            try:
                await channel.default_exchange.publish(
                    build_message(
                        message.body,
                        message_id=info.message_id,
                        event_type=info.event_type,
                        correlation_id=info.correlation_id,
                        headers=headers,
                    ),
                    routing_key=routing_key,
                )
            except Exception:
                logger.exception("falha ao reprocessar; mensagem continua na DLQ", extra={"queue": dlq})
                await message.nack(requeue=True)
                result.failed += 1
                break
            await message.ack()
            if not keep:
                result.replayed += 1
                logger.info(
                    "mensagem devolvida da DLQ",
                    extra={"queue": queue_name, "event_id": info.message_id, "replay_count": info.replay_count + 1},
                )
        return result
    finally:
        await connection.close()
