from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, JSON


from app.infrastructure.database import Base
from app.infrastructure.database.mixins import TimestampMixin
from app.domain.enums.audit import AuditAction


from uuid import UUID, uuid4

class AuditLogModel(Base, TimestampMixin):
    __tablename__ = 'login_acao'

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    entity: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    entity_id: Mapped[UUID | None] = mapped_column(
        String(36)
    )

    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
        index=True
    )

    old_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )
 
    new_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    ip: Mapped[str] = mapped_column(
        String(45),
        nullable=True
    )   

    user_agent: Mapped[str | None] = mapped_column(
        nullable=True,
    )   







