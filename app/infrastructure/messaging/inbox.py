"""Inbox de eventos: processa cada evento uma única vez por consumidor.

A marca em processed_event é gravada ANTES da alteração, na mesma transação.
Duas entregas simultâneas do mesmo evento (reentrega com prefetch > 1, retry,
réplicas do worker): o InnoDB trava a chave e a segunda espera o commit da
primeira; depois recebe chave duplicada e é tratada como duplicata (ack),
não como erro temporário. Se a primeira falhar, a segunda processa.
"""
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.events.envelope import EventEnvelope
from app.infrastructure.database.models.messaging.processed_event_model import ProcessedEventModel

logger = logging.getLogger("apoiamais.inbox")

Apply = Callable[[AsyncSession], Awaitable[None]]


def _is_processed_marker_conflict(exc: IntegrityError) -> bool:
    # 1062 = chave duplicada; só conta como duplicata se for a chave do inbox
    args = getattr(exc.orig, "args", ())
    return bool(args) and args[0] == 1062 and "processed_event.PRIMARY" in str(exc.orig)


async def process_once(
    session_factory: async_sessionmaker, consumer: str, envelope: EventEnvelope, apply: Apply
) -> bool:
    """Aplica `apply` na mesma transação da marca. Devolve False se era duplicata."""
    async with session_factory() as session:
        try:
            async with session.begin():
                session.add(
                    ProcessedEventModel(
                        consumer=consumer,
                        event_id=str(envelope.event_id),
                        event_type=envelope.event_type,
                    )
                )
                await session.flush()
                await apply(session)
        except IntegrityError as exc:
            if not _is_processed_marker_conflict(exc):
                raise
            logger.info("evento duplicado ignorado")
            return False
    return True
