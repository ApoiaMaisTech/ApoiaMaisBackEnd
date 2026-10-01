from app.domain.enums.user import UserRole
from app.domain.repositories.user_repository import UserRepository
from app.domain.exceptions.forbidden import ForbiddenActionException
from app.domain.exceptions.user_not_found import UserNotFoundException
from app.application.dto.create_user_response import UserResponse

class DeleteUserUseCase:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    # metodo que deleta um usuario pelo id, caso nao exista, levanta a excecao UserNotFoundException
    # deletable_roles restringe quais cargos podem ser removidos (None = qualquer um)
    async def execute(
        self,
        user_id: str,
        deletable_roles: set[UserRole] | None = None,
    ) -> UserResponse:
        user = await self.repository.get_by_id(user_id)

        if not user:
            raise UserNotFoundException("User not found")

        if deletable_roles is not None and UserRole(user.role) not in deletable_roles:
            raise ForbiddenActionException("Este tipo de conta não pode ser removido.")

        await self.repository.delete(user_id)

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role
        )
