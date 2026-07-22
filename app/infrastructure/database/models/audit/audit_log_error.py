from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin
from app.domain.enums.audit import LogLevel

from uuid import UUID, uuid4

class AuditLogErrorModel(Base, TimestampMixin):
    __tablename__ = 'log_error'

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    service: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    message: Mapped[str | None] = mapped_column(
        nullable=False
    )

    stack_trace: Mapped[str | None] = mapped_column(
        nullable=True
    )

    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel),
        default=LogLevel.ERROR,
        nullable=False
    )