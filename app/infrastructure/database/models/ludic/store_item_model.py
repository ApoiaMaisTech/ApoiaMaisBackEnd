from uuid import UUID, uuid4

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.store_item import StoreItemType
from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin


class StoreItemModel(Base, TimestampMixin):
    __tablename__ = "store_item"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    type: Mapped[StoreItemType] = mapped_column(
        Enum(StoreItemType),
        nullable=False,
        index=True,
    )

    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )