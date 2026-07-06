from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.application.dto.create_user_response import UserResponse

class ListUserUseCase:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    # metodo que lista todos os usuarios do repositorio e retorna uma lista de UserResponse
    async def execute(self) -> list[UserResponse]:
        users = await self.repository.list()

        return [
            UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role
            ) for user in users
        ]