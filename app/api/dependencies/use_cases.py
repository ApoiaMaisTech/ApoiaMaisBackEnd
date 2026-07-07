
### DEPENDENCIAS DE USE CASES CRUD DE USUARIO ###   
from app.api.dependencies.repositories import get_user_repository
from app.api.dependencies.services import get_password_service, get_jwt_service

from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
def get_create_user_usecase() -> CreateUserUseCase:
    return CreateUserUseCase(
        repository=get_user_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service()
    )

from app.application.use_cases.auth.login_usecase import LoginUseCase
def get_login_usecase() -> LoginUseCase:
    return LoginUseCase(
        user_repository=get_user_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service(),
        login_usecase = get_login_usecase()
    )

from app.application.use_cases.users.get_user_usecase import GetUserUseCase
def get_get_user_usecase() -> GetUserUseCase:
    return GetUserUseCase(
        repository=get_user_repository()
    )
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
def get_update_user_usecase() -> UpdateUserUseCase:
    return UpdateUserUseCase(
        repository=get_user_repository(),
        password_service=get_password_service()
    )
from app.application.use_cases.users.list_user_usecase import ListUserUseCase
def get_list_user_usecase() -> ListUserUseCase:
    return ListUserUseCase(
        repository=get_user_repository()
    )

from app.application.use_cases.users.delete_user_usecase import DeleteUserUseCase
def get_delete_user_usecase() -> DeleteUserUseCase:
    return DeleteUserUseCase(
        repository=get_user_repository()
    )



