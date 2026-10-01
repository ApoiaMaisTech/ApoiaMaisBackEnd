from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.enums.user import UserRole


class JwtService(ABC):
    @abstractmethod
    def generate_token(self, user_id: UUID, user_email: str, role: UserRole) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> dict:
        pass
