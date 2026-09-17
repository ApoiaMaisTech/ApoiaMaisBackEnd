from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.create_user_response import UserResponse
from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_service import PasswordService


class CreateUserUseCase:
    def __init__(
        self,
        repository: UserRepository,
        password_service: PasswordService,
    ):
        self.repository = repository
        self.password_service = password_service

    async def execute(
        self,
        request: CreateUserRequest,
        role: UserRole,
    ):
        existing_user = await self.repository.get_by_email(request.email)

        if existing_user:
            raise EmailAlreadyExistsException("Email already exists")

        password_hash = self.password_service.hash(request.password)

        user = User(
            id=None,
            name=request.name,
            email=request.email,
            password_hash=password_hash,
            role=role,
        )

        created_user = await self.repository.create(user)

        return UserResponse(
            id=created_user.id,
            name=created_user.name,
            email=created_user.email,
            role=created_user.role,
        )