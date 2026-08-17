from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin
from app.domain.enums.user import UserRole

from uuid import UUID, uuid4

class UserModel(Base,TimestampMixin):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4   
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[Enum] = mapped_column(
        Enum(UserRole),
        default=UserRole.TEACHER,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True
    )










