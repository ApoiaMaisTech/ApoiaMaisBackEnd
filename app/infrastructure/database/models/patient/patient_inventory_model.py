from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME

from app.infrastructure.database.base import Base


class PatientInventoryModel(Base):
    __tablename__ = "patient_inventory"

    patient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "patient.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
        index=True,
    )

    item_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "store_item.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
        index=True,
    )

    is_equipped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=3),
        nullable=False,
    )