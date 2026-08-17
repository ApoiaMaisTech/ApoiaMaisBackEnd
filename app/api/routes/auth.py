from app.application.dto.login_request import LoginRequest
from app.application.dto.token_response import TokenResponse

from app.api.dependencies.use_cases import get_login_usecase
from app.application.use_cases.auth.login_usecase import LoginUseCase

from app.domain.exceptions.user_not_found import UserNotFoundException
from app.domain.exceptions.invalid_credentials import InvalidCredentialsException

from fastapi import APIRouter, Depends, HTTPException


router = APIRouter()

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
