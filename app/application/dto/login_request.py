from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr
    # limite superior evita hash PBKDF2 de payloads enormes
    password: str = Field(min_length=1, max_length=128)
