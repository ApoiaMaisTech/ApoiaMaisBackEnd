from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
)

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin

from datetime import datetime

class PatientProgressModel(Base, TimestampMixin):
    __tablename__ = "patient_progress"

    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "stage_id",
            name="uq_patient_stage",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True,
    )

    patient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "patient.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    stage_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "stage.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    highest_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    earned_stars: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_played_at: Mapped[datetime | None] = mapped_column(
        DATETIME(fsp=3),
        nullable=True,
    )