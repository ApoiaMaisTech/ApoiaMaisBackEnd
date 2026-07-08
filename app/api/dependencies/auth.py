from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from uuid import UUID

# importacao dos basemodels e enums
from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.update_user_request import UpdateUserRequest
from app.domain.enums.user import UserRole
from app.application.dto.create_user_response import UserResponse

# importacao de use cases
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.application.use_cases.users.get_user_usecase import GetUserUseCase
from app.application.use_cases.users.list_user_usecase import ListUserUseCase
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
from app.application.use_cases.users.delete_user_usecase import DeleteUserUseCase

# importacao de dependencias
from app.api.dependencies.use_cases import get_create_user_usecase, get_get_user_usecase, get_list_user_usecase, get_update_user_usecase, get_delete_user_usecase
from app.api.dependencies.auth import get_current_teacher

# importacao de excecoes de dominio
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.domain.exceptions.user_not_found import UserNotFoundException

router = APIRouter()


# rotas de criacao de estudante
@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(
    request: CreateUserRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_usecase)
):
    try:
        return await use_case.execute(
            request=request,
            role=UserRole.STUDENT,
        )
    except EmailAlreadyExistsException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado."
        )


# rota de criacao de professor
@router.post("/teachers", status_code=status.HTTP_201_CREATED)
async def create_teacher(
    request: CreateUserRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_usecase)
):
    try:
        return await use_case.execute(
            request=request,
            role=UserRole.TEACHER,
        )
    except EmailAlreadyExistsException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado."
        )


# lista usuarios, utilizada só por qm tenha permissao
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_teacher = Depends(get_current_teacher),
    use_case: ListUserUseCase = Depends(get_list_user_usecase),
):
    return await use_case.execute()


# Buscar usuário por ID
@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    current_teacher = Depends(get_current_teacher),
    use_case: GetUserUseCase = Depends(get_get_user_usecase)
):
    try:
        return await use_case.execute(user_id)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )


# Atualizar usuário
@router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_teacher = Depends(get_current_teacher),
    use_case: UpdateUserUseCase = Depends(get_update_user_usecase)
):
    try:
        return await use_case.execute(
            user_id=user_id,
            request=request,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    except EmailAlreadyExistsException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado."
        )


# Deletar usuário
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    current_teacher = Depends(get_current_teacher),
    use_case: DeleteUserUseCase = Depends(get_delete_user_usecase)
):
    try:
        await use_case.execute(user_id)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )