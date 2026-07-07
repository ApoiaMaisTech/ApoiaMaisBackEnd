# importacao do enum q contem os cargos e do dto
from app.application.dto.create_user_request import CreateUserRequest
from app.domain.enums.user import UserRole

# importacao de excecoes e servicos
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_service import PasswordService
from app.application.dto.create_user_response import UserResponse

# construtor do use case de criacao de usuario, recebe o repositorio e o servico de senha como parametros
class CreateUserUseCase:
    def __init__(self, repository: UserRepository, password_service: PasswordService):
        self.repository = repository
        self.password_service = password_service

    async def execute(self,request: CreateUserRequest, role: UserRole):

        # verifica se o email ja existe no repositorio, caso exista, levanta a excecao
        existing_user = await self.repository.get_by_email(request.email)
        if existing_user:
            raise EmailAlreadyExistsException("Email already exists")

        # cria o hash da senha usando o servico de senha
        password_hash = self.password_service.hash(request.password)

        # cria o usuario com os dados do request e o hash da senha
        user = User(
            id=None,
            name=request.name,
            email=request.email,
            password_hash=password_hash,
            role=role
        )

        # salva o usuario no repositorio e retorna a resposta com os dados do usuario criado
        created_user = await self.repository.create(user)
        return UserResponse(
            id=created_user.id,
            name=created_user.name,
            email=created_user.email,
            role=created_user.role
        )


      