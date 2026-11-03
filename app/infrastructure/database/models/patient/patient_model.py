from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin
from app.domain.enums.happiness import Happiness


from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Date, JSON, ForeignKey, Uuid, Enum

from uuid import UUID, uuid4
from datetime import date

class PatientModel(Base, TimestampMixin):
    __tablename__ = 'patient'

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        index=True
    )

    # mesmo tipo de guardian.id (CHAR(32)); ver migration b7e2d4f1c9a3
    guardian_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("guardian.id", ondelete="SET NULL", name="fk_patient_guardian_id"),
        nullable=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    current_level: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        index=True
    )

    total_xp: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    total_coins: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    sequence_days: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    interest: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    current_happiness: Mapped[Happiness] = mapped_column(
        Enum(Happiness),
        default= Happiness.NEUTRAL,
        index=True
    )

    url_avatar: Mapped[str] = mapped_column(
        String(255),
        nullable=True

    )















        