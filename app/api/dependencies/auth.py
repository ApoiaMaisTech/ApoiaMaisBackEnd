from uuid import UUID

import jwt
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies.repositories import get_user_repository
from app.api.dependencies.services import get_jwt_service
from app.api.errors import ApiError
from app.domain.enums.user import UserRole
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.jwt_service import JwtService

# auto_error=False: sem token devolvemos 401 (o padrão do FastAPI é 403)
security = HTTPBearer(auto_error=False)


def _unauthorized(message: str, code: str = "UNAUTHORIZED") -> ApiError:
    return ApiError(
        status.HTTP_401_UNAUTHORIZED,
        message,
        code=code,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(message: str) -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, message, code="FORBIDDEN")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_service: JwtService = Depends(get_jwt_service),
    user_repository: UserRepository = Depends(get_user_repository),
) -> dict:
    if credentials is None:
        raise _unauthorized("Não autenticado.")

    try:
        payload = jwt_service.verify_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expirado.", "TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.", "TOKEN_INVALID")

    # token assinado mas com conteúdo inesperado também é inválido
    try:
        user_id = UUID(str(payload["user_id"]))
        UserRole(payload["role"])
    except (KeyError, ValueError):
        raise _unauthorized("Token inválido.", "TOKEN_INVALID")

    # O token é conferido contra o banco (uma busca por chave primária):
    # conta removida perde o acesso na hora, e o perfil vale o que está no banco,
    # não o que estava no token (perfil rebaixado não mantém privilégios até expirar).
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise _unauthorized("Token inválido.", "TOKEN_INVALID")

    return {
        "id": user.id,
        "email": user.email,
        "role": UserRole(user.role).value,
    }


def get_current_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != UserRole.TEACHER.value:
        raise _forbidden("Acesso permitido apenas para professores.")
    return current_user


def get_current_student(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != UserRole.STUDENT.value:
        raise _forbidden("Acesso permitido apenas para alunos.")
    return current_user


def require_roles(*roles: UserRole):
    allowed = {role.value for role in roles}

    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed:
            raise _forbidden("Acesso não permitido para este perfil.")
        return current_user

    return dependency
