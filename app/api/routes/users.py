from fastapi import APIRouter, Depends
from uuid import UUID

from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.update_user_request import UpdateUserRequest
from app.application.dto.create_user_response import UserResponse

from app.domain.enums.user import UserRole

from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.application.use_cases.users.get_user_usecase import GetUserUseCase
from app.application.use_cases.users.list_user_usecase import ListUserUseCase
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
from app.application.use_cases.users.delete_user_usecase import DeleteUserUseCase

from app.api.dependencies.use_cases import (
    get_create_user_usecase,
    get_get_user_usecase,
    get_list_user_usecase,
    get_update_user_usecase,
    get_delete_user_usecase,
)

from app.api.dependencies.auth import get_current_teacher


router = APIRouter()


# Criar estudante
@router.post("/students")
async def create_student(
    request: CreateUserRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_usecase),
):
    return await use_case.execute(
        request=request,
        role=UserRole.STUDENT,
    )


# Criar professor
@router.post("/teachers")
async def create_teacher(
    request: CreateUserRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_usecase),
):
    return await use_case.execute(
        request=request,
        role=UserRole.TEACHER,
    )


# Listar usuários
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_teacher=Depends(get_current_teacher),
    use_case: ListUserUseCase = Depends(get_list_user_usecase),
):
    return await use_case.execute()


# Buscar usuário por ID
@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    use_case: GetUserUseCase = Depends(get_get_user_usecase),
):
    return await use_case.execute(user_id)


# Atualizar usuário
@router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    use_case: UpdateUserUseCase = Depends(get_update_user_usecase),
):
    return await use_case.execute(
        user_id=user_id,
        request=request,
    )


# Deletar usuário
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    use_case: DeleteUserUseCase = Depends(get_delete_user_usecase),
):
    await use_case.execute(user_id)