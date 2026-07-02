# importacao do enum q contem os cargos e do dto
from application.dto.create_user_request import CreateUserRequest
from domain.enums.user import UserRole

# importacao de excecoes e servicos
from domain.exceptions.email_already_exists import EmailAlreadyExistsException
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.security.password import PasswordService
from application.dto.create_user_response import UserResponse

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


      