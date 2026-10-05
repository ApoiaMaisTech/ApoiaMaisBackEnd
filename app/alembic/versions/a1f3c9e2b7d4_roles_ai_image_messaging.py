"""roles completos, ai_image, outbox e inbox de eventos

Revision ID: a1f3c9e2b7d4
Revises: 4dd9c591f782
Create Date: 2026-10-05 12:00:00.000000

- user.role: a migration inicial só tinha STUDENT/TEACHER, mas o enum UserRole
  também tem ADMIN e DOCTOR (gravar médico/administrador falhava no MySQL).
- ai_image: metadados das ilustrações geradas por IA (o binário fica no storage).
- outbox_event: eventos gravados na mesma transação do dado de negócio e
  publicados no RabbitMQ pelo worker (outbox pattern).
- processed_event: eventos já consumidos, por consumidor (idempotência).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "a1f3c9e2b7d4"
down_revision: Union[str, Sequence[str], None] = "4dd9c591f782"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_ROLES = sa.Enum("STUDENT", "TEACHER", name="userrole")
_NEW_ROLES = sa.Enum("STUDENT", "TEACHER", "ADMIN", "DOCTOR", name="userrole")
_NOW = sa.text("CURRENT_TIMESTAMP(3)")


def upgrade() -> None:
    op.alter_column(
        "user",
        "role",
        existing_type=_OLD_ROLES,
        type_=_NEW_ROLES,
        existing_nullable=False,
    )

    op.create_table(
        "ai_image",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stage_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=80), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="aiimagestatus"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("completed_at", mysql.DATETIME(fsp=3), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=3), server_default=_NOW, nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=3), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["stage_id"], ["stage.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_ai_image_dedupe_key"),
    )
    op.create_index("ix_ai_image_stage_hash", "ai_image", ["stage_id", "prompt_hash"])
    op.create_index("ix_ai_image_requested_by", "ai_image", ["requested_by_user_id", "created_at"])
    op.create_index("ix_ai_image_status", "ai_image", ["status"])

    op.create_table(
        "outbox_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("routing_key", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("next_attempt_at", mysql.DATETIME(fsp=3), server_default=_NOW, nullable=False),
        sa.Column("published_at", mysql.DATETIME(fsp=3), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=3), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_event_pending", "outbox_event", ["published_at", "next_attempt_at"])

    op.create_table(
        "processed_event",
        sa.Column("consumer", sa.String(length=100), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", mysql.DATETIME(fsp=3), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("consumer", "event_id"),
    )


def downgrade() -> None:
    # drop_table já remove os índices (alguns sustentam FKs e não podem sair antes)
    op.drop_table("processed_event")
    op.drop_table("outbox_event")
    op.drop_table("ai_image")
    # volta ao enum antigo: falha se já houver ADMIN/DOCTOR gravados (proposital)
    op.alter_column(
        "user",
        "role",
        existing_type=_NEW_ROLES,
        type_=_OLD_ROLES,
        existing_nullable=False,
    )
