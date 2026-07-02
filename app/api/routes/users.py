from fastapi import APIRouter

# importacao dos basemodels, enums e use cases
from app.application.dto.create_user_request import(CreateUserRequest)
from domain.enums.user import UserRole
from application.use_cases.create_user_usecase import CreateUserUseCase 
from application.use_cases.users.update_user_usecase import UpdateUserUseCase
from application.use_cases.users.get_user_usecase import GetUserUseCase
from application.use_cases.users.delete_user_usecase import DeleteUserUseCase
from application.dto.update_user_request import UpdateUserRequest

router = APIRouter(prefix="/users", tags=["Users"])

# rotas de criacao de aluno
@router.post("/students")
async def create_student(
    request: CreateUserRequest,
    use_case: CreateUserUseCase
):
    return await use_case.execute(
        request=request,
        role=UserRole.STUDENT,
    )

# rota de criacao de professor
@router.post("/teachers")
async def create_teacher(
    request: CreateUserRequest,
    use_case: CreateUserUseCase 
):
    return await use_case.execute(
        request=request,
        role=UserRole.TEACHER,
    )

# Buscar usuário por ID
@router.get("/{user_id}")
async def get_user(
    user_id: int,
    use_case: GetUserUseCase,
):
    return await use_case.execute(user_id)


# Atualizar usuário
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    use_case: UpdateUserUseCase,
):
    return await use_case.execute(
        user_id=user_id,
        request=request,
    )


# Deletar usuário
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    use_case: DeleteUserUseCase,
):
    await use_case.execute(user_id)
