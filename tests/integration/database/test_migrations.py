"""Migrations em um banco descartável: instalação do zero, ida e volta e upgrade com dados.

Precisa de um usuário que possa criar bancos (no CI, o root do serviço MySQL):

    MIGRATIONS_TEST_ADMIN_URL=mysql+pymysql://root:root@127.0.0.1:3306 pytest tests/integration/database

Sem a variável, os testes são pulados. O Alembic roda pela linha de comando
(`python -m alembic`), exatamente como no container `migrate` do compose.
"""
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ADMIN_URL = os.getenv("MIGRATIONS_TEST_ADMIN_URL")
ALEMBIC_INI = "app/alembic.ini"

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="MIGRATIONS_TEST_ADMIN_URL não definido")

SCRIPT = ScriptDirectory.from_config(Config(ALEMBIC_INI))
# da mais antiga para a mais nova
REVISIONS = [rev.revision for rev in reversed(list(SCRIPT.walk_revisions()))]


@pytest.fixture
def scratch_db():
    """Cria um banco vazio só para o teste e apaga no final."""
    name = f"apoiamais_mig_{uuid4().hex[:10]}"
    admin = create_engine(make_url(ADMIN_URL).set(drivername="mysql+pymysql"))
    with admin.connect() as conn:
        conn.execute(text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"))
    try:
        yield name
    finally:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{name}`"))
        admin.dispose()


def _env(db_name: str) -> dict:
    url = make_url(ADMIN_URL)
    return {
        **os.environ,
        "DB_HOST": url.host or "127.0.0.1",
        "DB_PORT": str(url.port or 3306),
        "DB_USER": url.username or "root",
        "DB_PASSWORD": url.password or "",
        "DB_NAME": db_name,
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY", "migrations-test"),
    }


def alembic(db_name: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ALEMBIC_INI, *args],
        env=_env(db_name),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"alembic {' '.join(args)} falhou:\n{result.stdout}\n{result.stderr}"
    return result.stdout + result.stderr


def _engine(db_name: str):
    url = make_url(ADMIN_URL).set(drivername="mysql+pymysql", database=db_name)
    return create_engine(url)


def _tables(db_name: str) -> set[str]:
    engine = _engine(db_name)
    with engine.connect() as conn:
        rows = conn.execute(text("SHOW TABLES")).scalars().all()
    engine.dispose()
    return set(rows) - {"alembic_version"}


def test_instalacao_do_zero_chega_na_head_sem_drift(scratch_db):
    alembic(scratch_db, "upgrade", "head")

    assert SCRIPT.get_current_head() in alembic(scratch_db, "current")
    assert "No new upgrade operations detected" in alembic(scratch_db, "check")


def test_downgrade_completo_e_reinstalacao(scratch_db):
    alembic(scratch_db, "upgrade", "head")
    tables = _tables(scratch_db)

    alembic(scratch_db, "downgrade", "base")
    assert _tables(scratch_db) == set(), "downgrade base deixou tabelas para trás"

    alembic(scratch_db, "upgrade", "head")
    assert _tables(scratch_db) == tables


def test_escada_cada_revisao_sobe_desce_e_sobe(scratch_db):
    # pega downgrade quebrado em qualquer revisão, não só na última
    for revision in REVISIONS:
        alembic(scratch_db, "upgrade", revision)
        alembic(scratch_db, "downgrade", "-1")
        alembic(scratch_db, "upgrade", revision)


def test_upgrade_preserva_dados_existentes(scratch_db):
    first = REVISIONS[0]
    alembic(scratch_db, "upgrade", first)

    user_id, guardian_id, patient_id, world_id, stage_id = (uuid4() for _ in range(5))
    engine = _engine(scratch_db)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user (id, email, password_hash, name, role, is_active) "
                "VALUES (:id, 'antigo@example.com', 'hash', 'Usuário Antigo', 'TEACHER', 1)"
            ),
            {"id": user_id.hex},
        )
        conn.execute(
            text(
                "INSERT INTO guardian (id, name, parentage, phone, email) "
                "VALUES (:id, 'Responsável', 'mãe', '11999999999', 'resp@example.com')"
            ),
            {"id": guardian_id.hex},
        )
        conn.execute(
            text(
                "INSERT INTO patient (id, guardian_id, name, birth_date, current_level, total_xp, "
                "total_coins, sequence_days, current_happiness) "
                "VALUES (:id, :g, 'Criança', '2018-05-01', 1, 0, 0, 0, 'HAPPY')"
            ),
            {"id": patient_id.hex, "g": guardian_id.hex},
        )
        conn.execute(
            text("INSERT INTO patient_clinical (patient_id, clinical_rate) VALUES (:p, 'observação')"),
            {"p": patient_id.hex},
        )
        conn.execute(
            text("INSERT INTO world (id, name, `order`, is_active) VALUES (:id, 'Floresta', 1, 1)"),
            {"id": world_id.hex},
        )
        conn.execute(
            text(
                "INSERT INTO stage (id, world_id, name, `order`, difficulty, xp_reward, coin_reward) "
                "VALUES (:id, :w, 'Vogais', 1, 1, 10, 5)"
            ),
            {"id": stage_id.hex, "w": world_id.hex},
        )

    alembic(scratch_db, "upgrade", "head")

    with engine.begin() as conn:
        assert conn.execute(text("SELECT role FROM user WHERE id = :id"), {"id": user_id.hex}).scalar() == "TEACHER"
        assert conn.execute(
            text("SELECT guardian_id FROM patient WHERE id = :id"), {"id": patient_id.hex}
        ).scalar() == guardian_id.hex
        assert conn.execute(
            text("SELECT clinical_rate FROM patient_clinical WHERE patient_id = :p"), {"p": patient_id.hex}
        ).scalar() == "observação"
        assert conn.execute(text("SELECT name FROM stage WHERE id = :id"), {"id": stage_id.hex}).scalar() == "Vogais"

        # o que a head trouxe funciona com os dados antigos
        conn.execute(
            text(
                "INSERT INTO user (id, email, password_hash, name, role, is_active) "
                "VALUES (:id, 'medico@example.com', 'hash', 'Médica', 'DOCTOR', 1)"
            ),
            {"id": uuid4().hex},
        )
        conn.execute(
            text(
                "INSERT INTO ai_image (id, stage_id, requested_by_user_id, dedupe_key, prompt, prompt_hash, "
                "status, storage_key) VALUES (:id, :s, :u, 'k1', 'p', 'h', 'PENDING', 'ai-images/x.png')"
            ),
            {"id": uuid4().hex, "s": stage_id.hex, "u": user_id.hex},
        )
    engine.dispose()


def test_upgrade_normaliza_uuid_com_hifen_gravado_sem_fk(scratch_db):
    # dados antigos gravados com FOREIGN_KEY_CHECKS=0 (importação manual, por exemplo)
    alembic(scratch_db, "upgrade", "a1f3c9e2b7d4")
    guardian_id, patient_id = uuid4(), uuid4()
    engine = _engine(scratch_db)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO guardian (id, name, parentage, phone, email) "
                "VALUES (:id, 'Responsável', 'pai', '11999999999', 'r@example.com')"
            ),
            {"id": guardian_id.hex},
        )
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.execute(
            text(
                "INSERT INTO patient (id, guardian_id, name, birth_date, current_level, total_xp, "
                "total_coins, sequence_days, current_happiness) "
                "VALUES (:id, :g, 'Criança', '2018-05-01', 1, 0, 0, 0, 'HAPPY')"
            ),
            {"id": patient_id.hex, "g": str(guardian_id)},
        )
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    alembic(scratch_db, "upgrade", "head")

    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT guardian_id FROM patient WHERE id = :id"), {"id": patient_id.hex}
        ).scalar() == guardian_id.hex
    engine.dispose()
