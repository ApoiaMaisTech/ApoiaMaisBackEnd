from app.domain.repositories.user_repository import UserRepository
from app.domain.exceptions.user_not_found import UserNotFoundException
from app.application.dto.create_user_response import UserResponse

class DeleteUserUseCase:
    
    def __init__(self, repository: UserRepository):
        self.repository = repository

    # metodo que deleta um usuario pelo id, caso nao exista, levanta a excecao UserNotFoundException
    async def execute(self, user_id: str) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        
        if not user:
            raise UserNotFoundException("User not found")
        
        await self.repository.delete(user_id)

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role
        )