from fastapi import APIRouter

# importacao dos basemodels, enums e use cases
from app.application.dto.create_user_request import(CreateUserRequest)
from domain.enums.user import UserRole
from application.use_cases.users  import CreateUserUseCase, GetUserUseCase, UpdateUserUseCase, DeleteUserUseCase
from application.dto.update_user_request import UpdateUserRequest

router = APIRouter(prefix="/users", tags=["Users"])

# rotas de criacao de paciente
@router.post("/patients")
async def create_patient(
    request: CreateUserRequest,
    use_case: CreateUserUseCase
):
    return await use_case.execute(
        request=request,
        role=UserRole.STUDENT,
    )

# rota de criacao de medico
@router.post("/doctors")
async def create_doctor(
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

