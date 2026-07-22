from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Text


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin


from uuid import UUID, uuid4

class PatientClinicalModel(Base, TimestampMixin):
    __tablename__ = 'patient_clinical'


    patient_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("patient.id", ondelete="SET NULL"),
        primary_key=True,
        nullable=True,
        index=True
    )

    clinical_rate: Mapped[str] = mapped_column(
        Text()
    )