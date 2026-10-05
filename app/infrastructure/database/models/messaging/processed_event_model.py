from datetime import datetime

from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.types import DateTime3, utcnow


class ProcessedEventModel(Base):
    """Inbox: eventos já processados por cada consumidor (idempotência)."""

    __tablename__ = "processed_event"

    consumer: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime3, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP(3)")
    )
