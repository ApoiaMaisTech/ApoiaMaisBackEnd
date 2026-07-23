from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, Text, BigInteger


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin
from app.domain.enums.file import FileOwnerType, FileCategory

from uuid import UUID, uuid4

class FileModel(Base, TimestampMixin):
    __tablename__ = 'files'


    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True
    )

    owner_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    owner_type: Mapped[FileOwnerType] = mapped_column(
        Enum(FileOwnerType),
        nullable=False
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    category: Mapped[FileCategory] = mapped_column(
        Enum(FileCategory),
        nullable=False,
        index=True
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
