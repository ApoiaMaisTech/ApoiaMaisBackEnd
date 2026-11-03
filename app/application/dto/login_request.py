from pydantic import BaseModel, Field

from app.application.dto.validators import Email


class LoginRequest(BaseModel):
    email: Email
    # limite superior evita hash PBKDF2 de payloads enormes
    password: str = Field(min_length=1, max_length=128)
