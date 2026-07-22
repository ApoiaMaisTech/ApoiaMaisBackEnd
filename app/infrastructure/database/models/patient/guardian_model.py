from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin


from uuid import UUID, uuid4

class GuardianModel(Base,TimestampMixin):
    __tablename__ = "guardian"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    parentage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )


