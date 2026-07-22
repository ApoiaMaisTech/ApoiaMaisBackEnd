from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models.auth.user_model import UserModel


class SqlUserRepository(UserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, user: UserModel) -> UserModel:
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> UserModel | None:
        return await self.db_session.get(UserModel, user_id)

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self) -> list[UserModel]:
        stmt = select(UserModel)
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, user: UserModel) -> UserModel:
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