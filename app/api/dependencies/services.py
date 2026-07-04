### DEPENDENCIAS DA API PARA SERVICOS DE SEGURANCA (JWT E PASSWORD) ###
from infrastructure.security.password import PasswordService
def get_password_service() -> PasswordService:
    return PasswordService()

from infrastructure.security.jwt import JWTService
def get_jwt_service() -> JWTService:
    return JWTService()


