from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.types import DateTime3, utcnow


class OutboxEventModel(Base):
    """Evento a publicar, gravado na mesma transação do dado que o originou."""

    __tablename__ = "outbox_event"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)  # = event_id
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # envelope JSON pronto
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime3, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP(3)")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime3, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime3, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP(3)")
    )
