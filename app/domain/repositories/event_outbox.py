from abc import ABC, abstractmethod

from app.application.events.envelope import EventEnvelope


class EventOutbox(ABC):
    """Publica eventos de forma confiável: grava no outbox (mesma transação do dado)
    e o api-worker leva ao RabbitMQ. Quem chama nunca fala com o broker."""

    @abstractmethod
    async def publish(self, event: EventEnvelope) -> None: ...
