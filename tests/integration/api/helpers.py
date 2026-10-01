from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from app.api.dependencies.services import get_jwt_service
from app.core.config import settings
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository

PASSWORD = "senha-correta-123"


class InMemoryUserRepository(UserRepository):
    """Repositório falso: exercita use cases e rotas reais sem MySQL."""

    def __init__(self):
        self.users: dict[UUID, User] = {}

    async def create(self, user: User) -> User:
        user.id = user.id or uuid4()
        self.users[user.id] = user
        return user

    async def get_by_id(self, user_id) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def list(self) -> list[User]:
        return list(self.users.values())

    async def update(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def delete(self, user_id) -> None:
        self.users.pop(user_id, None)


def auth_header(user: User) -> dict[str, str]:
    token = get_jwt_service().generate_token(user.id, user.email, user.role)
    return {"Authorization": f"Bearer {token}"}


def forge_token(payload: dict, secret: str | None = None) -> dict[str, str]:
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5), **payload}
    token = jwt.encode(payload, secret or settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}
