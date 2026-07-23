from uuid import UUID, uuid4

from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
    Text,
    Uuid,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.ai_content_type import AIContentType
from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin


class AIContentModel(Base, TimestampMixin):
    __tablename__ = "ai_content"

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

    stage_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "stage.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    type: Mapped[AIContentType] = mapped_column(
        Enum(AIContentType),
        nullable=False,
        index=True,
    )

    generated_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )