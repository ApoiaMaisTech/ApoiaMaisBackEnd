"""FKs de paciente com o mesmo tipo da chave referenciada

Revision ID: b7e2d4f1c9a3
Revises: a1f3c9e2b7d4
Create Date: 2026-11-03 12:00:00.000000

patient.guardian_id e patient_clinical.patient_id eram VARCHAR(36), mas apontam
para guardian.id e patient.id, que são CHAR(32) (sa.Uuid grava o hex sem hífens).
Um UUID gravado no formato com hífens (str(uuid)) nunca casava com a chave e a
FK recusava o INSERT (erro 1452). As colunas passam a ser CHAR(32) (sa.Uuid),
e valores já gravados com hífens são normalizados.

As FKs ganham nome explícito (antes era o nome gerado pelo MySQL, *_ibfk_N).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7e2d4f1c9a3"
down_revision: Union[str, Sequence[str], None] = "a1f3c9e2b7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabela, coluna, tabela referenciada, ON DELETE, nullable, nome da FK nova)
_FKS = (
    ("patient", "guardian_id", "guardian", "SET NULL", True, "fk_patient_guardian_id"),
    ("patient_clinical", "patient_id", "patient", "CASCADE", False, "fk_patient_clinical_patient_id"),
)


def _drop_fk(table: str, column: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if fk["constrained_columns"] == [column]:
            op.drop_constraint(fk["name"], table, type_="foreignkey")


def upgrade() -> None:
    for table, column, referred, ondelete, nullable, fk_name in _FKS:
        _drop_fk(table, column)
        op.execute(
            sa.text(f"UPDATE `{table}` SET `{column}` = REPLACE(`{column}`, '-', '') WHERE `{column}` LIKE '%-%'")
        )
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=36),
            type_=sa.Uuid(),
            existing_nullable=nullable,
            nullable=nullable,
        )
        op.create_foreign_key(fk_name, table, referred, [column], ["id"], ondelete=ondelete)


def downgrade() -> None:
    # os valores ficam no formato hex (32 caracteres), que cabe em VARCHAR(36)
    for table, column, referred, ondelete, nullable, fk_name in reversed(_FKS):
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.alter_column(
            table,
            column,
            existing_type=sa.Uuid(),
            type_=sa.String(length=36),
            existing_nullable=nullable,
            nullable=nullable,
        )
        op.create_foreign_key(None, table, referred, [column], ["id"], ondelete=ondelete)
