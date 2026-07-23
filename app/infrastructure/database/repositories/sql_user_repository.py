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
        await self.db_session.refresh()


    async def get_by_id(self, user_id: UUID) -> UserModel | None:
        return await self.db_session.get(UserModel, user_id)

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)


        result = await self.db_session.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
            
        return UserModel()


    async def list(self) -> list[UserModel]:
        stmt = select(UserModel)

        result = await self.db_session.execute(stmt)
        user_db = result.scalars().all()
        
        return [
            UserModel() for u in user_db]


    async def update(self, user: UserModel) -> UserModel:
        user = await self.db_session.merge(user)

        await self.db_session.commit()
        await self.db_session.refresh()
        
        return UserModel()

    async def delete(self, user_id: UUID) -> None:
        db_user = await self.db_session.get(user_id)
        if db_user is None:
            return
        await self.db_session.delete(db_user)
        await self.db_session.commit()