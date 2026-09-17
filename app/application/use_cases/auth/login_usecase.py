from app.domain.enums.user import UserRole  
from app.application.dto.login_request import LoginRequest
from app.application.dto.token_response import TokenResponse, UserData
from app.domain.repositories.user_repository import UserRepository
from app.domain.exceptions.user_not_found import UserNotFoundException
from app.domain.exceptions.invalid_credentials import InvalidCredentialsException
from app.domain.services.password_service import PasswordService
from app.domain.services.jwt_service import JwtService


class LoginUseCase:
    def __init__(self, user_repository: UserRepository, password_service: PasswordService, jwt_service: JwtService):
        self.user_repository = user_repository
        self.password_service = password_service
        self.jwt_service = jwt_service

    async def execute(self, request: LoginRequest) -> TokenResponse:
        # busca o usuario pelo email
        user = await self.user_repository.get_by_email(request.email)
        if not user:
            raise UserNotFoundException("User not found")

        # verifica se a senha esta correta
        if not self.password_service.verify(request.password, user.password_hash):
            raise InvalidCredentialsException()

        # gera o token de acesso
        access_token = self.jwt_service.generate_token(user.id, user.email, user.role)

        role_value = user.role.value if isinstance(user.role, UserRole ) else user.role

        return TokenResponse(
            token=access_token,
            user=UserData(
                id=user.id,
                name=user.name,
                email=user.email,
                role=role_value,
            ),
        )