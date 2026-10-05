# DEPENDÊNCIAS DA API PARA O BANCO DE DADOS

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)
from app.infrastructure.database.repositories.sql_ai_image_repository import (
    SqlAiImageRepository,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_user_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> SqlUserRepository:
    return SqlUserRepository(db_session=db_session)

def get_ai_image_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> SqlAiImageRepository:
    return SqlAiImageRepository(db_session=db_session)
