# DEPENDÊNCIAS DA API PARA O BANCO DE DADOS

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_user_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> SqlUserRepository:
    return SqlUserRepository(db_session=db_session)