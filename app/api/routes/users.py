from fastapi import APIRouter

# importacao dos basemodels, enums e use cases
from app.application.dto.create_user_request import(CreateUserRequest)
from domain.enums.user import UserRole
from application.use_cases.create_user_usecase import CreateUserUseCase

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
