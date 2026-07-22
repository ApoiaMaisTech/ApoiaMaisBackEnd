from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, Text
from sqlalchemy.dialects.mysql import DATETIME
from app.domain.enums.notification import NotificationType

from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin


from uuid import UUID, uuid4
from datetime import datetime

class NotificationModel(Base, TimestampMixin):
    __tablename__ = 'notification'

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True
    )

    receiver_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        nullable=False,
        index=True

    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    message:  Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    read: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        index=True
    )

    read_at: Mapped[datetime | None] = mapped_column(
    DATETIME(fsp=3),
    nullable=True,
) 





