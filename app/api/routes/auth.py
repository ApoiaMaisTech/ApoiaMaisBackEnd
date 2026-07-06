from application.dto.login_request import LoginRequest
from application.dto.token_response import TokenResponse

from app.api.dependencies.use_cases import get_login_usecase
from app.api.dependencies.auth import get_current_doctor
from application.use_cases.auth.login_usecase import LoginUseCase
from application.use_cases.users.list_user_usecase import ListUserUseCase
from api.dependencies.use_cases import  get_list_user_usecase
from application.dto.create_user_response import UserResponse



from domain.exceptions.user_not_found import UserNotFoundException
from domain.exceptions.invalid_credentials import InvalidCredentialsException


from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/auth", tags=["auth"])

# Rota pública responsável por autenticar o usuário e gerar um token JWT.
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_usecase)
):
    try:
        return await use_case.execute(request)
    
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    
    except InvalidCredentialsException:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    

# lista usuarios, utilizada só por qm tenha permissao
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_doctor = Depends(get_current_doctor),
    use_case: ListUserUseCase = Depends(get_list_user_usecase),
):
    return await use_case.execute()
    
