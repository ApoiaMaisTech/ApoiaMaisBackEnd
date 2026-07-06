### DEPENDENCIAS DE AUTENTICACAO E AUTORIZACAO ###  


from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

from domain.exceptions.invalid_credentials import InvalidCredentialsException

from api.dependencies.services  import get_jwt_service
from api.dependencies.repositories  import get_user_repository

from infrastructure.security.jwt import JWTService
from infrastructure.database.repositories.sql_user_repository import SqlUserRepository

from fastapi import Depends
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        jwt_service: JWTService = Depends(get_jwt_service),
        user_repository: SqlUserRepository = Depends(get_user_repository)):

        payload = jwt_service.verify_token(token)
        user_id = payload.get("user_id")

        user = await user_repository.get_user_by_id(user_id)
        if not user:
            raise InvalidCredentialsException()
        return user


### DEPENDENCIA DE OBTENCAO DO USUARIO ATUAL POR TIPO, DOUTOR E PACIENTE ###
from fastapi import Depends, HTTPException, status
from domain.enums.user import UserRole
from infrastructure.database.models import Usuario

async def get_current_doctor(
        current_user: Usuario = Depends(get_current_user)
):
    if current_user.cargo != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Somente médicos podem acessar este recurso."
        )
    return current_user

async def get_current_patient(
        current_user: Usuario = Depends(get_current_user)
):
    if current_user.cargo != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado."
        )
    return current_user




