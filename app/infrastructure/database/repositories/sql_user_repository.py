from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.user_repository import UserRepository
from app.domain.entities.user import User  # IMPORTANTE: Importar a entidade de domínio
from app.infrastructure.database.models import Usuario


class SqlUserRepository(UserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, user: User) -> User:  
        db_user = Usuario(
            id=user.id,
            nome=user.name,
            email=user.email,
            senha_hash=user.password_hash,
            cargo=user.role.value if hasattr(user.role, 'value') else user.role,
            esta_ativo=True  
        )

        self.db_session.add(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)

        return User(
            id=db_user.id,
            name=db_user.nome,
            email=db_user.email,
            password_hash=db_user.senha_hash,
            role=user.role
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        db_user = await self.db_session.get(Usuario, user_id)
        if not db_user:
            return None
        return User(
            id=db_user.id,
            name=db_user.nome,
            email=db_user.email,
            password_hash=db_user.senha_hash,
            role=db_user.cargo
        )

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.db_session.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
            
        return User(
            id=db_user.id,
            name=db_user.nome,
            email=db_user.email,
            password_hash=db_user.senha_hash,
            role=db_user.cargo
        )

    async def list(self) -> list[User]:
        stmt = select(Usuario)
        result = await self.db_session.execute(stmt)
        usuarios_db = result.scalars().all()
        
        return [
            User(
                id=u.id,
                name=u.nome,
                email=u.email,
                password_hash=u.senha_hash,
                role=u.cargo
            ) for u in usuarios_db
        ]

    async def update(self, user: User) -> User:
        db_user = Usuario(
            id=user.id,
            nome=user.name,
            email=user.email,
            senha_hash=user.password_hash,
            cargo=user.role.value if hasattr(user.role, 'value') else user.role
        )
        db_user = await self.db_session.merge(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)
        
        return User(
            id=db_user.id,
            name=db_user.nome,
            email=db_user.email,
            password_hash=db_user.senha_hash,
            role=user.role
        )

    async def delete(self, user_id: UUID) -> None:
        db_user = await self.db_session.get(Usuario, user_id)
        if db_user is None:
            return
        await self.db_session.delete(db_user)
        await self.db_session.commit()