"""Retenção de dados (LGPD): só sai o que passou do prazo, e nada além disso."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.infrastructure.database.retention import MIN_AUDIT_DAYS, RetentionPolicy, apply_retention
from app.infrastructure.database.session import AsyncSessionLocal

NOW = datetime(2026, 6, 1, 12, 0, 0)


async def _exec(sql: str, **params):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            return await session.execute(text(sql), params)


async def _exists(table: str, column: str, value: str) -> bool:
    result = await _exec(f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` = :v", v=value)
    return result.scalar() > 0


@pytest_asyncio.fixture
async def rows():
    """Uma linha velha e uma recente por regra; tudo é apagado no final."""
    ids = {k: uuid4().hex for k in (
        "pe_old", "pe_new", "ob_old", "ob_new", "ob_pending_old",
        "le_old", "le_new", "nt_read_old", "nt_unread_old", "nt_read_new", "la_old", "la_new",
    )}
    old = NOW - timedelta(days=400)
    recent = NOW - timedelta(days=1)

    for key, when in (("pe_old", old), ("pe_new", recent)):
        await _exec(
            "INSERT INTO processed_event (consumer, event_id, event_type, processed_at) VALUES ('teste-retencao', :id, 't', :w)",
            id=ids[key], w=when,
        )
    for key, when, published in (("ob_old", old, old), ("ob_new", recent, recent), ("ob_pending_old", old, None)):
        await _exec(
            "INSERT INTO outbox_event (id, event_type, routing_key, correlation_id, body, attempts, next_attempt_at, published_at, created_at) "
            "VALUES (:id, 't', 't', 'c', '{}', 0, :w, :p, :w)",
            id=ids[key], w=when, p=published,
        )
    for key, when in (("le_old", old), ("le_new", recent)):
        await _exec(
            "INSERT INTO log_error (id, user_id, service, message, level, created_at, updated_at) "
            "VALUES (:id, 'u', 'teste', 'm', 'ERROR', :w, :w)",
            id=ids[key], w=when,
        )
    for key, when, read in (("nt_read_old", old, 1), ("nt_unread_old", old, 0), ("nt_read_new", recent, 1)):
        await _exec(
            "INSERT INTO notification (id, receiver_id, type, title, message, `read`, created_at, updated_at) "
            "VALUES (:id, 'u', 'SYSTEM', 't', 'm', :r, :w, :w)",
            id=ids[key], w=when, r=read,
        )
    for key, when in (("la_old", old), ("la_new", NOW - timedelta(days=MIN_AUDIT_DAYS - 1))):
        await _exec(
            "INSERT INTO login_acao (id, user_id, entity, action, created_at, updated_at) "
            "VALUES (:id, 'u', 'user', 'LOGIN', :w, :w)",
            id=ids[key], w=when,
        )

    yield ids

    await _exec("DELETE FROM processed_event WHERE consumer = 'teste-retencao'")
    for table in ("outbox_event", "log_error", "notification", "login_acao"):
        await _exec(f"DELETE FROM `{table}` WHERE id IN :ids".replace(":ids", "(" + ",".join(f"'{v}'" for v in ids.values()) + ")"))


@pytest.mark.asyncio
async def test_remove_so_o_que_passou_do_prazo(rows):
    removed = await apply_retention(AsyncSessionLocal, RetentionPolicy(), now=NOW, batch_size=1)

    assert all(count >= 1 for count in removed.values()), removed

    assert not await _exists("processed_event", "event_id", rows["pe_old"])
    assert await _exists("processed_event", "event_id", rows["pe_new"])

    assert not await _exists("outbox_event", "id", rows["ob_old"])
    assert await _exists("outbox_event", "id", rows["ob_new"])
    # evento ainda não publicado nunca é apagado, por mais velho que seja
    assert await _exists("outbox_event", "id", rows["ob_pending_old"])

    assert not await _exists("log_error", "id", rows["le_old"])
    assert await _exists("log_error", "id", rows["le_new"])

    assert not await _exists("notification", "id", rows["nt_read_old"])
    assert await _exists("notification", "id", rows["nt_unread_old"])
    assert await _exists("notification", "id", rows["nt_read_new"])

    assert not await _exists("login_acao", "id", rows["la_old"])
    assert await _exists("login_acao", "id", rows["la_new"])


def test_auditoria_nao_pode_ficar_abaixo_do_marco_civil():
    with pytest.raises(ValueError):
        RetentionPolicy(audit_log_days=MIN_AUDIT_DAYS - 1)


def test_prazo_precisa_ser_positivo():
    with pytest.raises(ValueError):
        RetentionPolicy(processed_event_days=0)
