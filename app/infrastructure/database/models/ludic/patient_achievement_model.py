from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME

from app.infrastructure.database.base import Base


class PatientAchievementModel(Base):
    __tablename__ = "patient_achievement"

    patient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "patient.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
        index=True,
    )

    achievement_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "achievement.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
        index=True,
    )

    achieved_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=3),
        server_default=func.now(),
        nullable=False,
    )