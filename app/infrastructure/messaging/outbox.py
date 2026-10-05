import logging
from datetime import timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.events.envelope import EventEnvelope
from app.infrastructure.database.models.messaging.outbox_event_model import OutboxEventModel
from app.infrastructure.database.types import utcnow

logger = logging.getLogger("apoiamais.outbox")

MAX_BACKOFF_SECONDS = 300


class Publisher(Protocol):
    async def publish(
        self, body: bytes, *, routing_key: str, message_id: str, event_type: str, correlation_id: str
    ) -> None: ...


def add_to_outbox(session: AsyncSession, envelope: EventEnvelope) -> None:
    """Registra o evento na sessão atual; vai para o banco no mesmo commit do dado de negócio."""
    session.add(
        OutboxEventModel(
            id=envelope.event_id,
            event_type=envelope.event_type,
            routing_key=envelope.event_type,
            correlation_id=envelope.correlation_id,
            body=envelope.to_json(),
            attempts=0,
            next_attempt_at=utcnow(),
        )
    )


def backoff_seconds(attempts: int) -> int:
    return min(2 ** attempts, MAX_BACKOFF_SECONDS)


class OutboxRelay:
    """Lê eventos pendentes do outbox e publica no RabbitMQ.

    FOR UPDATE SKIP LOCKED permite várias réplicas do worker sem publicar o
    mesmo evento duas vezes ao mesmo tempo. Se cair entre publicar e marcar,
    o evento sai de novo: por isso todo consumidor é idempotente (event_id).
    """

    def __init__(self, session_factory: async_sessionmaker, publisher: Publisher, batch_size: int = 50):
        self._session_factory = session_factory
        self._publisher = publisher
        self._batch_size = batch_size

    async def run_once(self) -> int:
        published = 0
        async with self._session_factory() as session:
            async with session.begin():
                now = utcnow()
                stmt = (
                    select(OutboxEventModel)
                    .where(
                        OutboxEventModel.published_at.is_(None),
                        OutboxEventModel.next_attempt_at <= now,
                    )
                    .order_by(OutboxEventModel.created_at)
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
                rows = (await session.execute(stmt)).scalars().all()

                for row in rows:
                    try:
                        await self._publisher.publish(
                            row.body.encode(),
                            routing_key=row.routing_key,
                            message_id=str(row.id),
                            event_type=row.event_type,
                            correlation_id=row.correlation_id,
                        )
                    except Exception as exc:
                        row.attempts += 1
                        row.last_error = f"{type(exc).__name__}: {exc}"[:500]
                        row.next_attempt_at = utcnow() + timedelta(seconds=backoff_seconds(row.attempts))
                        logger.warning(
                            "falha ao publicar evento do outbox",
                            extra={"event_id": str(row.id), "attempts": row.attempts},
                        )
                        continue
                    row.published_at = utcnow()
                    published += 1
        return published
