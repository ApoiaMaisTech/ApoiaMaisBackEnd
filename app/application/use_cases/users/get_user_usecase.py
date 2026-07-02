from domain.repositories.user_repository import UserRepository
from domain.exceptions import UserNotFoundException
from application.dto.create_user_response import UserResponse

from uuid import UUID

class GetUserUseCase:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    # metodo q obtem um usuario pelo id, caso nao exista, levanta a excecao UserNotFoundException
    async def execute(self, user_id: UUID) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role
        )
