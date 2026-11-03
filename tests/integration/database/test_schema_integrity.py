"""Integridade do schema no banco migrado (alembic upgrade head).

Roda contra o mesmo MySQL dos outros testes de integração e não deixa dados
(cada teste faz rollback).
"""
from datetime import date
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

import app.infrastructure.database.models  # noqa: F401  (registra todos os models no metadata)
from app.infrastructure.database.base import Base
from app.infrastructure.database.models.patient.guardian_model import GuardianModel
from app.infrastructure.database.models.patient.patient_clinical import PatientClinicalModel
from app.infrastructure.database.models.patient.patient_model import PatientModel
from app.infrastructure.database.session import engine

ALEMBIC_INI = "app/alembic.ini"

pytestmark = pytest.mark.asyncio


def _head() -> str:
    return ScriptDirectory.from_config(Config(ALEMBIC_INI)).get_current_head()


async def test_banco_esta_na_head():
    async with engine.connect() as conn:
        current = await conn.run_sync(lambda c: MigrationContext.configure(c).get_current_revision())
    assert current == _head(), "rode: python -m alembic -c app/alembic.ini upgrade head"


async def test_models_e_migrations_sem_drift():
    # equivale a `alembic check`: se falhar, falta migration (ou o model está errado)
    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata)
        )
    assert diff == [], f"models e banco divergem: {diff}"


async def test_toda_fk_tem_o_mesmo_tipo_da_chave_referenciada():
    query = text(
        """
        SELECT k.TABLE_NAME, k.COLUMN_NAME, c1.COLUMN_TYPE,
               k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, c2.COLUMN_TYPE
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.COLUMNS c1
          ON c1.TABLE_SCHEMA = k.TABLE_SCHEMA AND c1.TABLE_NAME = k.TABLE_NAME
         AND c1.COLUMN_NAME = k.COLUMN_NAME
        JOIN information_schema.COLUMNS c2
          ON c2.TABLE_SCHEMA = k.TABLE_SCHEMA AND c2.TABLE_NAME = k.REFERENCED_TABLE_NAME
         AND c2.COLUMN_NAME = k.REFERENCED_COLUMN_NAME
        WHERE k.TABLE_SCHEMA = DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL
        """
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(query)).all()

    assert rows, "nenhuma FK encontrada"
    divergentes = [f"{r[0]}.{r[1]} {r[2]} -> {r[3]}.{r[4]} {r[5]}" for r in rows if r[2] != r[5]]
    assert divergentes == []


async def test_toda_fk_do_banco_tem_regra_de_delete_explicita():
    # sem ON DELETE, apagar o pai falha (RESTRICT) e o direito de exclusão (LGPD) emperra
    query = text(
        "SELECT TABLE_NAME, CONSTRAINT_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE()"
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(query)).all()

    assert {r[2] for r in rows} <= {"CASCADE", "SET NULL"}, rows


@pytest.mark.parametrize(
    "table,columns",
    [
        ("user", ("email",)),
        ("ai_image", ("dedupe_key",)),
        ("patient_progress", ("patient_id", "stage_id")),
        ("world", ("order",)),
    ],
)
async def test_restricoes_de_unicidade_existem(table, columns):
    query = text(
        "SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND NON_UNIQUE = 0 GROUP BY INDEX_NAME"
    )
    async with engine.connect() as conn:
        uniques = {tuple(cols.split(",")) for _, cols in (await conn.execute(query, {"t": table})).all()}
    assert columns in uniques


async def test_chave_do_inbox_de_eventos_e_consumidor_mais_evento():
    query = text(
        "SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'processed_event' AND INDEX_NAME = 'PRIMARY'"
    )
    async with engine.connect() as conn:
        assert (await conn.execute(query)).scalar() == "consumer,event_id"


async def test_paciente_com_responsavel_e_dado_clinico_pelo_orm(db_session):
    # antes da b7e2d4f1c9a3 este fluxo falhava com IntegrityError 1452 (VARCHAR(36) -> CHAR(32))
    guardian = GuardianModel(id=uuid4(), name="Responsável", parentage="mãe", phone="11999999999", email="resp@example.com")
    patient = PatientModel(
        id=uuid4(), name="Criança", birth_date=date(2018, 5, 1), guardian_id=guardian.id
    )
    db_session.add(guardian)
    await db_session.flush()
    db_session.add(patient)
    await db_session.flush()
    db_session.add(PatientClinicalModel(patient_id=patient.id, clinical_rate="observação"))
    await db_session.flush()

    stored = (await db_session.execute(select(PatientModel).where(PatientModel.id == patient.id))).scalar_one()
    assert stored.guardian_id == guardian.id


async def test_apagar_paciente_apaga_o_dado_clinico(db_session):
    patient = PatientModel(id=uuid4(), name="Criança", birth_date=date(2018, 5, 1))
    db_session.add(patient)
    await db_session.flush()
    db_session.add(PatientClinicalModel(patient_id=patient.id, clinical_rate="observação"))
    await db_session.flush()

    await db_session.execute(delete(PatientModel).where(PatientModel.id == patient.id))
    restante = await db_session.execute(
        select(PatientClinicalModel).where(PatientClinicalModel.patient_id == patient.id)
    )
    assert restante.first() is None


async def test_dado_clinico_sem_paciente_e_recusado(db_session):
    db_session.add(PatientClinicalModel(patient_id=uuid4(), clinical_rate="órfão"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
