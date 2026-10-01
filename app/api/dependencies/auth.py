from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies.services import get_jwt_service
from app.domain.enums.user import UserRole
from app.domain.services.jwt_service import JwtService

# auto_error=False: sem token devolvemos 401 (o padrão do FastAPI é 403)
security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_service: JwtService = Depends(get_jwt_service),
) -> dict:
    if credentials is None:
        raise _unauthorized("Não autenticado.")

    try:
        payload = jwt_service.verify_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expirado.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.")

    # token assinado mas com conteúdo inesperado também é inválido
    try:
        return {
            "id": UUID(str(payload["user_id"])),
            "email": payload.get("user_email"),
            "role": UserRole(payload["role"]).value,
        }
    except (KeyError, ValueError):
        raise _unauthorized("Token inválido.")


def get_current_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != UserRole.TEACHER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para professores.",
        )
    return current_user


def get_current_student(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para alunos.",
        )
    return current_user
