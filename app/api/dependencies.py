from infrastructure.database.session import AsyncSessionLocal
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

from infrastructure.database.repositories.sql_user_repository import SqlUserRepository
def get_user_repository() -> SqlUserRepository:
    return SqlUserRepository(db_session=AsyncSessionLocal())


from infrastructure.security.password import PasswordService
def get_password_service() -> PasswordService:
    return PasswordService()

from infrastructure.security.jwt import JWTService
def get_jwt_service() -> JWTService:
    return JWTService()

from application.use_cases.users.create_user_usecase import CreateUserUseCase
def get_create_user_usecase() -> CreateUserUseCase:
    return CreateUserUseCase(
        repository=get_user_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service()
    )

from application.use_cases.auth.login_usecase import LoginUseCase
def get_login_usecase() -> LoginUseCase:
    return LoginUseCase(
        user_repository=get_user_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service()
    )

from application.use_cases.users.get_user_usecase import GetUserUseCase
def get_get_user_usecase() -> GetUserUseCase:
    return GetUserUseCase(
        repository=get_user_repository()
    )

from application.use_cases.users.update_user_usecase import UpdateUserUseCase
def get_update_user_usecase() -> UpdateUserUseCase:
    return UpdateUserUseCase(
        repository=get_user_repository(),
        password_service=get_password_service()
    )
from application.use_cases.users.list_user_usecase import ListUserUseCase
def get_list_user_usecase() -> ListUserUseCase:
    return ListUserUseCase(
        repository=get_user_repository()
    )


from application.use_cases.users.delete_user_usecase import DeleteUserUseCase
def get_delete_user_usecase() -> DeleteUserUseCase:
    return DeleteUserUseCase(
        repository=get_user_repository()
    )