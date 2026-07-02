from app.application.dto.login_request import LoginRequest
from app.application.dto.token_response import TokenResponse
from domain.repositories.user_repository import UserRepository
from domain.exceptions import UserNotFoundException, InvalidCredentialsException
from infrastructure.security.password import PasswordService
from infrastructure.security.jwt import JwtService

class LoginUseCase:
    def __init__(self, user_repository: UserRepository, password_service: PasswordService, jwt_service: JwtService):
        self.user_repository = user_repository
        self.password_service = password_service
        self.jwt_service = jwt_service

    async def execute(self, request: LoginRequest) -> TokenResponse:
        # busca o usuario pelo email
        user = await self.user_repository.get_by_email(request.email)
        if not user:
            raise UserNotFoundException()

        # verifica se a senha esta correta
        if not self.password_service.verify(request.password, user.password_hash):
            raise InvalidCredentialsException()

        # gera o token de acesso
        access_token = self.jwt_service.generate_token(user.id, user.email, user.role)

        return TokenResponse(access_token=access_token)
    