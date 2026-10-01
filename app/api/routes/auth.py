from app.application.dto.login_request import LoginRequest
from app.application.dto.token_response import TokenResponse

from app.api.dependencies.rate_limit import rate_limit
from app.api.dependencies.use_cases import get_login_usecase
from app.application.use_cases.auth.login_usecase import LoginUseCase
from app.core.config import settings

from fastapi import APIRouter, Depends


router = APIRouter()

# Rota pública responsável por autenticar o usuário e gerar um token JWT.
# Erros (401 credenciais, 429 limite) são tratados pelos handlers globais.
@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("login", settings.RATE_LIMIT_LOGIN))],
)
async def login(
    request: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_usecase)
):
    return await use_case.execute(request)
