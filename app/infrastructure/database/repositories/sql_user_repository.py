from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository

from app.infrastructure.database.models.auth.user_model import UserModel
from app.infrastructure.database.mappers.user_mapper import UserMapper

class SqlUserRepository(UserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, user: User) -> User:
        db_user = UserMapper._to_model(user)
        self.db_session.add(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)

        return UserMapper._to_entity(db_user)

    async def get_by_id(self, user_id: UUID) -> User | None:
        db_user = await self.db_session.get(UserModel, user_id)
        if not db_user:
            return None
        
        return UserMapper._to_entity(db_user)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)

        result = await self.db_session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            return None

        return UserMapper._to_entity(db_user)

    async def list(self) -> list[User]:
        stmt = select(UserModel)

        result = await self.db_session.execute(stmt)
        users_db = result.scalars().all()

        return [UserMapper._to_entity(u) for u in users_db]

    async def update(self, user: User) -> User:
        db_user = UserMapper._to_model(user)
        db_user = await self.db_session.merge(db_user)

        await self.db_session.commit()
        await self.db_session.refresh(db_user)

        return UserMapper._to_entity(db_user)

    async def delete(self, user_id: UUID) -> None:
        db_user = await self.db_session.get(UserModel, user_id)
        if db_user is None:
            return
        await self.db_session.delete(db_user)
        await self.db_session.commit()