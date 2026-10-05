import random
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import delete

import app.infrastructure.database.models  # noqa: F401
from app.infrastructure.database.models.ludic.stage_model import StageModel
from app.infrastructure.database.models.ludic.world_model import WorldModel
from app.infrastructure.database.models.messaging.outbox_event_model import OutboxEventModel
from app.infrastructure.database.session import AsyncSessionLocal


@pytest_asyncio.fixture
async def stage_id():
    """Mundo + fase reais no MySQL; apagar o mundo apaga fase e imagens (CASCADE)."""
    world_id, sid = uuid4(), uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            WorldModel(id=world_id, name="Floresta das Letras", order=random.randint(10**6, 10**9), is_active=True)
        )
        await session.flush()
        session.add(StageModel(id=sid, world_id=world_id, name=f"Vogais {sid.hex[:6]}", order=1))
        await session.commit()

    yield sid

    async with AsyncSessionLocal() as session:
        await session.execute(delete(WorldModel).where(WorldModel.id == world_id))
        await session.commit()


@pytest_asyncio.fixture
async def clean_outbox():
    """Os testes de outbox partem de uma fila vazia (o banco de teste é compartilhado)."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(OutboxEventModel))
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(delete(OutboxEventModel))
        await session.commit()


@pytest_asyncio.fixture
async def user_id():
    from app.domain.entities.user import User
    from app.domain.enums.user import UserRole
    from app.infrastructure.database.repositories.sql_user_repository import SqlUserRepository

    async with AsyncSessionLocal() as session:
        repository = SqlUserRepository(session)
        user = await repository.create(
            User(id=uuid4(), name="Aluno", email=f"{uuid4().hex}@example.com", password_hash="x", role=UserRole.STUDENT)
        )
    yield user.id
    async with AsyncSessionLocal() as session:
        await SqlUserRepository(session).delete(user.id)
