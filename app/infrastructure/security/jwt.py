from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pydantic import EmailStr

from app.domain.enums.user import UserRole
from app.domain.services.jwt_service import JwtService


class JwtServiceImpl(JwtService):
    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_minutes: int = 30):
        # sem fallback: um segredo padrão permitiria forjar tokens
        if not secret_key:
            raise ValueError("JWT secret key is required")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_minutes = expiration_minutes

    def generate_token(self, user_id: UUID, user_email: EmailStr, role: UserRole) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": str(user_id),
            "user_email": str(user_email),
            "role": role.value if isinstance(role, UserRole) else role,
            "iat": now,
            "exp": now + timedelta(minutes=self.expiration_minutes),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        return jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            options={"require": ["exp", "user_id", "role"]},
        )
