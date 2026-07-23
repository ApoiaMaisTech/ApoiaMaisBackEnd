from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin


class StageModel(Base, TimestampMixin):
    __tablename__ = "stage"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True,
    )

    world_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "world.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    difficulty: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    xp_reward: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )

    coin_reward: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )