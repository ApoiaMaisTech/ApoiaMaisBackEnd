import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection

from app.infrastructure.messaging.topology import build_message, declare_exchanges


class RabbitPublisher:
    """Publica no apoiamais.events com publisher confirms (espera o ack do broker)."""

    def __init__(self, url: str):
        self._url = url
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._events: AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        exchanges = await declare_exchanges(self._channel)
        self._events = exchanges["events"]

    async def publish(
        self, body: bytes, *, routing_key: str, message_id: str, event_type: str, correlation_id: str
    ) -> None:
        if self._events is None:
            raise RuntimeError("publisher não conectado")
        message = build_message(
            body, message_id=message_id, event_type=event_type, correlation_id=correlation_id
        )
        # com publisher_confirms, o await só retorna depois do ack do broker
        await self._events.publish(message, routing_key=routing_key)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
