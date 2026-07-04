from application.dto.login_request import LoginRequest
from application.dto.token_response import TokenResponse

from app.api.dependencies import get_login_usecase
from application.use_cases.auth.login_usecase import LoginUseCase

from domain.exceptions import UserNotFoundException, InvalidCredentialsException

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

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