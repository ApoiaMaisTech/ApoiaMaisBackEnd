from uuid import UUID, uuid4

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin


class AchievementModel(Base, TimestampMixin):
    __tablename__ = "achievement"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    icon_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    xp_bonus: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )