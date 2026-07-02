from abc import ABC, abstractmethod

# classe abstrata com metodos para hash e verificação de senha
class PasswordService(ABC):

    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        pass