from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Text, Uuid


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin


from uuid import UUID, uuid4

class PatientClinicalModel(Base, TimestampMixin):
    __tablename__ = 'patient_clinical'


    # dado de saúde pertence ao paciente: sem paciente, não existe (CASCADE, como no banco).
    # SET NULL aqui deixaria prontuário órfão, e chave primária não pode ser nula.
    # Mesmo tipo de patient.id (CHAR(32)); ver migration b7e2d4f1c9a3.
    patient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("patient.id", ondelete="CASCADE", name="fk_patient_clinical_patient_id"),
        primary_key=True,
        nullable=False,
        index=True
    )

    clinical_rate: Mapped[str] = mapped_column(
        Text()
    )