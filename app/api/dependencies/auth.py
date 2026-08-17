from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.enums.user import UserRole
from app.infrastructure.security.jwt import JwtServiceImpl

security = HTTPBearer()


def get_jwt_service() -> JwtServiceImpl:
    return JwtServiceImpl()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_service: JwtServiceImpl = Depends(get_jwt_service),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt_service.verify_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )

    return {
        "id": UUID(payload["user_id"]),
        "email": payload["user_email"],
        "role": payload["role"],
    }


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
