from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.update_user_request import UpdateUserRequest
from app.application.dto.create_user_response import UserResponse

from app.core.config import settings
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

from app.api.dependencies.auth import get_current_teacher, get_current_user
from app.api.dependencies.rate_limit import rate_limit


router = APIRouter()

# Matriz de autorização (testada em tests/integration/api/test_authorization_matrix.py):
#   rota                    anônimo  aluno           professor
#   POST /students          401      403             201
#   POST /teachers          401      403             201
#   GET  /                  401      403             200
#   GET  /{id}              401      só o próprio    200
#   PUT  /{id}              401      só o próprio    só o próprio
#   DELETE /{id}            401      403             só contas de aluno

limit_user_creation = Depends(rate_limit("user-creation", settings.RATE_LIMIT_USER_CREATION))


def _ensure_self(current_user: dict, user_id: UUID) -> None:
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode acessar a sua própria conta.",
        )


# Criar estudante
@router.post(
    "/students",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[limit_user_creation],
)
async def create_student(
    request: CreateUserRequest,
    current_teacher=Depends(get_current_teacher),
    use_case: CreateUserUseCase = Depends(get_create_user_usecase),
):
    return await use_case.execute(
        request=request,
        role=UserRole.STUDENT,
    )


# Criar professor
@router.post(
    "/teachers",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[limit_user_creation],
)
async def create_teacher(
    request: CreateUserRequest,
    current_teacher=Depends(get_current_teacher),
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
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user=Depends(get_current_user),
    use_case: GetUserUseCase = Depends(get_get_user_usecase),
):
    if current_user["role"] != UserRole.TEACHER.value:
        _ensure_self(current_user, user_id)
    return await use_case.execute(user_id)


# Atualizar usuário (email e senha: só o dono da conta)
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user=Depends(get_current_user),
    use_case: UpdateUserUseCase = Depends(get_update_user_usecase),
):
    _ensure_self(current_user, user_id)
    return await use_case.execute(
        user_id=user_id,
        request=request,
    )


# Deletar usuário (professor remove alunos; contas de professor não)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_teacher=Depends(get_current_teacher),
    use_case: DeleteUserUseCase = Depends(get_delete_user_usecase),
):
    await use_case.execute(user_id, deletable_roles={UserRole.STUDENT})
