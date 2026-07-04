from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.user_repository import UserRepository
from infrastructure.database.models import Usuario


class SqlUserRepository(UserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, user: Usuario) -> Usuario:
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> Usuario | None:
        return await self.db_session.get(Usuario, user_id)

    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self) -> list[Usuario]:
        stmt = select(Usuario)
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, user: Usuario) -> Usuario:
        user = await self.db_session.merge(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user

    async def delete(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)

        if user is None:
            return
        await self.db_session.delete(user)
        await self.db_session.commit()