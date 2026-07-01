# lib q permite criar classes abstratas
from abc import ABC, abstractmethod
from domain.entities.user import User
class UserRepository(ABC):

    # metodos de manipulacao de dados dos usuarios
    @abstractmethod
    async def create(self, user: User) -> User:
        ...
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        ...
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...
    @abstractmethod
    async def list(self) -> list[User]:
        ...
    @abstractmethod
    async def update(self, user: User) -> User:
        ...
    @abstractmethod
    async def delete(self, user_id: str) -> None:
        ...
        