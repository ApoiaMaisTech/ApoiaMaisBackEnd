### DEPENDENCIAS DA API PARA SERVICOS DE SEGURANCA (JWT E PASSWORD) ###
from app.core.config import settings
from app.domain.services.password_service import PasswordService
from app.domain.services.jwt_service import JwtService
from app.infrastructure.security.password import PasswordServiceImpl
from app.infrastructure.security.jwt import JwtServiceImpl


def get_password_service() -> PasswordService:
    return PasswordServiceImpl()


def get_jwt_service() -> JwtService:
    return JwtServiceImpl(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


