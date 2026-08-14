import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pydantic import EmailStr

from app.domain.enums.user import UserRole


class JwtServiceImpl:
    def __init__(self, secret_key: str | None = None, algorithm: str = "HS256", expiration_minutes: int = 30):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "secret-key")
        self.algorithm = algorithm
        self.expiration_minutes = expiration_minutes

    def generate_token(self, user_id: UUID, user_email: EmailStr, role: UserRole) -> str:
        payload = {
            "user_id": str(user_id),
            "user_email": str(user_email),
            "role": role.value if isinstance(role, UserRole) else role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self.expiration_minutes),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])