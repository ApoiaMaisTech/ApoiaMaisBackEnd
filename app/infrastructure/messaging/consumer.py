import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika
import structlog
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractIncomingMessage
from pydantic import ValidationError

from app.application.events.envelope import EventEnvelope
from app.core.redaction import safe_error_text
from app.infrastructure.messaging.topology import (
    DLX_EXCHANGE,
    ERROR_HEADER,
    RETRY_COUNT_HEADER,
    RETRY_EXCHANGE,
    build_message,
    declare_consumer_queue,
    retry_delay_for,
    retry_queue_name,
)

logger = logging.getLogger("apoiamais.consumer")

Handler = Callable[[EventEnvelope], Awaitable[None]]


class PermanentError(Exception):
    """Erro que não melhora tentando de novo (evento inválido, versão desconhecida...)."""


def retry_count_of(message: AbstractIncomingMessage) -> int:
    try:
        return max(0, int((message.headers or {}).get(RETRY_COUNT_HEADER, 0) or 0))
    except (TypeError, ValueError):
        return 0


class EventConsumer:
    """Consumidor com ack manual, prefetch, retry com backoff e DLQ.

    - sucesso: ack
    - erro temporário: republica em <fila>.retry.<delay> com x-retry-count+1 e dá ack
    - erro permanente ou tentativas esgotadas: republica na DLQ e dá ack
    - falha ao republicar: nack com requeue (x-delivery-limit da fila quorum limita o loop)
    - encerramento: para de receber, espera as mensagens em andamento (drain) e só então fecha
    Os handlers precisam ser idempotentes: a mesma mensagem pode chegar mais de uma vez.
    """

    def __init__(
        self,
        url: str,
        queue_name: str,
        handlers: dict[tuple[str, int], Handler],
        max_retries: int = 3,
        prefetch: int = 10,
        drain_timeout: float = 15.0,
    ):
        self._url = url
        self.queue_name = queue_name
        self._handlers = handlers
        self._max_retries = max_retries
        self._prefetch = prefetch
        self._drain_timeout = drain_timeout
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queue = None
        self._consumer_tag: str | None = None
        self._consuming = False
        self._inflight = 0
        self._idle = asyncio.Event()
        self._idle.set()

    @property
    def bindings(self) -> list[str]:
        return sorted({event_type for event_type, _ in self._handlers})

    async def start(self) -> None:
        """Conecta, declara a topologia e começa a consumir (uma vez, sem reconexão)."""
        # Conexão simples (não robusta) + laço explícito em run(): a restauração
        # automática do connect_robust não recriou o consumidor depois de um
        # restart do RabbitMQ (visto no teste ponta a ponta). Aqui cada reconexão
        # redeclara a fila e volta a consumir.
        self._connection = await aio_pika.connect(self._url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=self._prefetch)
        queue = await declare_consumer_queue(self._channel, self.queue_name, self.bindings)
        self._queue = queue
        self._consumer_tag = await queue.consume(self.on_message)
        self._consuming = True
        logger.info("consumidor iniciado", extra={"queue": self.queue_name})

    async def run(self, stop: asyncio.Event) -> None:
        """Consome até stop, reconectando com backoff exponencial (1s..30s)."""
        backoff = 1.0
        while not stop.is_set():
            closed = asyncio.Event()
            try:
                await self.start()
                assert self._connection is not None
                self._connection.close_callbacks.add(lambda *_: closed.set())
                backoff = 1.0
                waiters = [asyncio.ensure_future(stop.wait()), asyncio.ensure_future(closed.wait())]
                _, pending = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
            except Exception:
                logger.warning("consumidor sem conexão com o RabbitMQ", exc_info=True)
            finally:
                self._consuming = False
                await self.close()
            if stop.is_set():
                break
            logger.info("reconectando consumidor", extra={"backoff_seconds": backoff})
            try:
                await asyncio.wait_for(stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 30.0)

    @property
    def inflight(self) -> int:
        return self._inflight

    async def close(self) -> None:
        """Para de receber, espera as mensagens em andamento (até drain_timeout) e fecha.

        As que ainda estavam só no prefetch (não começaram) voltam para a fila sozinhas
        quando o canal fecha. Se o tempo acabar, as em andamento também voltam
        (não houve ack) e serão reentregues: os handlers são idempotentes.
        """
        queue, tag = self._queue, self._consumer_tag
        self._queue, self._consumer_tag = None, None
        connected = self._connection is not None and not self._connection.is_closed
        if queue is not None and tag is not None and connected:
            try:
                await queue.cancel(tag)
            except Exception:
                logger.debug("erro ao cancelar o consumo", exc_info=True)
        # sem conexão não há como dar ack: esperar não adianta (serão reentregues)
        if self._inflight and connected:
            logger.info("aguardando mensagens em andamento", extra={"inflight": self._inflight})
            try:
                await asyncio.wait_for(self._idle.wait(), timeout=self._drain_timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    "tempo de drain esgotado; mensagens em andamento serão reentregues",
                    extra={"inflight": self._inflight},
                )

        connection, self._connection = self._connection, None
        if connection is not None and not connection.is_closed:
            try:
                await connection.close()
            except Exception:
                logger.debug("erro ao fechar conexão", exc_info=True)

    @property
    def is_connected(self) -> bool:
        return (
            self._consuming
            and self._connection is not None
            and not self._connection.is_closed
        )

    async def on_message(self, message: AbstractIncomingMessage) -> None:
        self._inflight += 1
        self._idle.clear()
        try:
            await self._process(message)
        finally:
            self._inflight -= 1
            if self._inflight == 0:
                self._idle.set()

    async def _process(self, message: AbstractIncomingMessage) -> None:
        retry_count = retry_count_of(message)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=message.correlation_id or "-",
            event_id=message.message_id or "-",
            queue=self.queue_name,
        )
        try:
            try:
                envelope = EventEnvelope.model_validate_json(message.body)
            except ValidationError as exc:
                raise PermanentError(f"envelope inválido: {exc.error_count()} erro(s)") from exc

            handler = self._handlers.get((envelope.event_type, envelope.version))
            if handler is None:
                raise PermanentError(
                    f"evento não suportado: {envelope.event_type} v{envelope.version}"
                )
            structlog.contextvars.bind_contextvars(event_type=envelope.event_type)
            await handler(envelope)
        except PermanentError as exc:
            logger.error("evento inválido enviado para a DLQ", extra={"error": safe_error_text(exc)})
            await self._dead_letter(message, retry_count, exc)
        except Exception as exc:
            if retry_count >= self._max_retries:
                logger.exception("tentativas esgotadas, evento enviado para a DLQ")
                await self._dead_letter(message, retry_count, exc)
            else:
                logger.warning(
                    "erro temporário, agendando nova tentativa",
                    extra={"attempt": retry_count + 1, "error": type(exc).__name__},
                )
                await self._retry(message, retry_count + 1, exc)
        else:
            await message.ack()
        finally:
            structlog.contextvars.clear_contextvars()

    async def _republish(
        self, message: AbstractIncomingMessage, exchange_name: str, routing_key: str, headers: dict
    ) -> None:
        assert self._channel is not None
        exchange = await self._channel.get_exchange(exchange_name, ensure=False)
        await exchange.publish(
            build_message(
                message.body,
                message_id=message.message_id or "",
                event_type=message.type or "",
                correlation_id=message.correlation_id or "",
                headers=headers,
            ),
            routing_key=routing_key,
        )

    async def _retry(self, message: AbstractIncomingMessage, attempt: int, exc: Exception) -> None:
        headers = {**(message.headers or {}), RETRY_COUNT_HEADER: attempt, ERROR_HEADER: _short(exc)}
        target = retry_queue_name(self.queue_name, retry_delay_for(attempt))
        try:
            await self._republish(message, RETRY_EXCHANGE, target, headers)
        except Exception:
            logger.exception("falha ao agendar retry; devolvendo para a fila")
            await message.nack(requeue=True)
            return
        await message.ack()

    async def _dead_letter(self, message: AbstractIncomingMessage, attempt: int, exc: Exception) -> None:
        headers = {**(message.headers or {}), RETRY_COUNT_HEADER: attempt, ERROR_HEADER: _short(exc)}
        try:
            await self._republish(message, DLX_EXCHANGE, self.queue_name, headers)
        except Exception:
            logger.exception("falha ao publicar na DLQ; devolvendo para a fila")
            await message.nack(requeue=True)
            return
        await message.ack()


def _short(exc: Exception) -> str:
    # vai no header x-last-error, que fica guardado no RabbitMQ (retry e DLQ)
    return safe_error_text(exc, 300)
