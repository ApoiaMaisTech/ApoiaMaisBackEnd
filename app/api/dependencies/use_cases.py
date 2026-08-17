from fastapi import Depends

# Importação dos Repositórios e Serviços
from app.api.dependencies.repositories import get_user_repository
from app.api.dependencies.services import get_password_service, get_jwt_service

# Importação dos Casos de Uso
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.application.use_cases.auth.login_usecase import LoginUseCase
from app.application.use_cases.users.get_user_usecase import GetUserUseCase
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
from app.application.use_cases.users.list_user_usecase import ListUserUseCase
from app.application.use_cases.users.delete_user_usecase import DeleteUserUseCase


# DEPENDENCIAS DE USE CASES CRUD DE USUARIO

def get_create_user_usecase(
    repository=Depends(get_user_repository),
    password_service=Depends(get_password_service)
) -> CreateUserUseCase:
    return CreateUserUseCase(
        repository=repository,
        password_service=password_service
    )


def get_login_usecase(
    user_repository=Depends(get_user_repository),
    password_service=Depends(get_password_service),
    jwt_service=Depends(get_jwt_service)
) -> LoginUseCase:
    return LoginUseCase(
        user_repository=user_repository,
        password_service=password_service,
        jwt_service=jwt_service
    )


def get_get_user_usecase(
    repository=Depends(get_user_repository)
) -> GetUserUseCase:
    return GetUserUseCase(
        repository=repository
    )


def get_update_user_usecase(
    repository=Depends(get_user_repository),
    password_service=Depends(get_password_service)
) -> UpdateUserUseCase:
    return UpdateUserUseCase(
        repository=repository,
        password_service=password_service
    )


def get_list_user_usecase(
    repository=Depends(get_user_repository)
) -> ListUserUseCase:
    return ListUserUseCase(
        repository=repository
    )


def get_delete_user_usecase(
    repository=Depends(get_user_repository)
) -> DeleteUserUseCase:
    return DeleteUserUseCase(
        repository=repository
    )
