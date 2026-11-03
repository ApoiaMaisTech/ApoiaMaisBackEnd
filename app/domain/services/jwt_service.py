from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.enums.user import UserRole


class JwtService(ABC):
    @abstractmethod
    # o token leva só o necessário (id e perfil): o payload de um JWT é legível por
    # qualquer um que o tenha (base64), então dado pessoal como o email fica de fora (LGPD)
    def generate_token(self, user_id: UUID, role: UserRole) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> dict:
        pass
