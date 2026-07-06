### DEPENDENCIAS DE AUTENTICACAO E AUTORIZACAO ###  


from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

from app.domain.exceptions.invalid_credentials import InvalidCredentialsException

from app.api.dependencies.services  import get_jwt_service
from app.api.dependencies.repositories  import get_user_repository

from app.domain.services.jwt_service import JwtService
from app.infrastructure.database.repositories.sql_user_repository import SqlUserRepository

from fastapi import Depends
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        jwt_service: JwtService = Depends(get_jwt_service),
        user_repository: SqlUserRepository = Depends(get_user_repository)):

        payload = jwt_service.verify_token(token)
        user_id = payload.get("user_id")

        user = await user_repository.get_user_by_id(user_id)
        if not user:
            raise InvalidCredentialsException()
        return user


### DEPENDENCIA DE OBTENCAO DO USUARIO ATUAL POR TIPO, PROFESSOR E ESTUDANTE ###
from fastapi import Depends, HTTPException, status
from app.domain.enums.user import UserRole
from app.infrastructure.database.models import Usuario

async def get_current_teacher(
        current_user: Usuario = Depends(get_current_user)
):
    if current_user.cargo != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Somente professores podem acessar este recurso."
        )
    return current_user

async def get_current_student(
        current_user: Usuario = Depends(get_current_user)
):
    if current_user.cargo != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado."
        )
    return current_user




