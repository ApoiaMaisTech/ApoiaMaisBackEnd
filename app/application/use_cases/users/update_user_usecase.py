from app.application.dto.update_user_request import UpdateUserRequest
from app.domain.repositories.user_repository import UserRepository
from app.application.dto.create_user_response import UserResponse
from app.domain.exceptions.user_not_found import UserNotFoundException
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.domain.services.password_service import PasswordService


from uuid import UUID

class UpdateUserUseCase:

    def __init__(self, repository: UserRepository, password_service: PasswordService):
        self.repository = repository
        self.password_service = password_service
        
    
    async def execute(self, user_id: UUID, request: UpdateUserRequest) -> UserResponse:

        # obtem o usuario pelo id, caso nao exista, levanta a excecao UserNotFoundException
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        
        # verifica se o email ja existe no banco de dados
        existing_user = await self.repository.get_by_email(request.email)
        if existing_user and existing_user.id != user_id:
            raise EmailAlreadyExistsException()
        
        # atualiza o usuario com os novos dados
        user.email = request.email
        user.password_hash = self.password_service.hash(request.password)

        updated_user =await self.repository.update(user)

        return UserResponse(
            id=updated_user.id,
            name=updated_user.name,
            email=updated_user.email,
            role=updated_user.role
        )









        


        


