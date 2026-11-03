"""O engine com pool (padrão em produção) funciona com o driver real.

Os demais testes rodam sem pool (tests/conftest.py), então este é o único que pega
incompatibilidades do pool com aiomysql/SQLAlchemy (ex.: pool_pre_ping quebrado).
"""
import asyncio

import pytest
from sqlalchemy import text

from app.infrastructure.database.session import DATABASE_URL, build_engine

pytestmark = pytest.mark.asyncio


async def test_pool_reaproveita_conexoes_e_aguenta_concorrencia():
    engine = build_engine(DATABASE_URL, pool_size=3)
    try:
        async def query():
            async with engine.connect() as conn:
                return (await conn.execute(text("SELECT CONNECTION_ID()"))).scalar()

        ids = await asyncio.gather(*(query() for _ in range(30)))

        assert len(ids) == 30
        # 30 consultas, no máximo pool_size + max_overflow conexões distintas
        assert len(set(ids)) <= 3 + 10
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


async def test_conexao_derrubada_e_substituida():
    engine = build_engine(DATABASE_URL, pool_size=1)
    try:
        async with engine.connect() as conn:
            first = (await conn.execute(text("SELECT CONNECTION_ID()"))).scalar()
        # simula o MySQL derrubando a conexão ociosa (restart, wait_timeout)
        killer = build_engine(DATABASE_URL, pool_size=0)
        async with killer.connect() as conn:
            await conn.execute(text(f"KILL {int(first)}"))
        await killer.dispose()

        # a primeira tentativa pode falhar (conexão morta é invalidada); a seguinte funciona
        for attempt in range(2):
            try:
                async with engine.connect() as conn:
                    second = (await conn.execute(text("SELECT CONNECTION_ID()"))).scalar()
                break
            except Exception:
                if attempt == 1:
                    raise
        assert second != first
    finally:
        await engine.dispose()
