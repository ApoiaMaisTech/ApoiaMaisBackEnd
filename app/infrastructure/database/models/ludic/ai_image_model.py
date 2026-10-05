from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.ai_image import AiImageStatus
from app.infrastructure.database.base import Base
from app.infrastructure.database.types import DateTime3, utcnow


class AiImageModel(Base):
    """Metadados de uma ilustração gerada por IA. O binário fica no storage."""

    __tablename__ = "ai_image"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    stage_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("stage.id", ondelete="CASCADE"), nullable=False
    )
    # quem disparou (o jogo, em nome do aluno); nunca vai para o provedor de IA
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    # "<stage>:<hash do prompt>" enquanto a imagem é válida; NULL quando falha.
    # O índice único impede dois jobs iguais quando várias crianças abrem a fase juntas.
    dedupe_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AiImageStatus] = mapped_column(Enum(AiImageStatus), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime3, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime3, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP(3)")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime3,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )
