from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

from app.api.dependencies.services import get_jwt_service
from app.domain.services.jwt_service import JwtService


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    jwt_service: JwtService = Depends(get_jwt_service),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais ausentes.",
        )

    try:
        return jwt_service.verify_token(credentials.credentials)
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )


def get_current_teacher(payload: dict = Depends(get_current_user_payload)) -> dict:
    if payload.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para professores.",
        )
    return payload
