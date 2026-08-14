from uuid import UUID

from pydantic import BaseModel

from app.domain.enums.user import UserRole


class UserData(BaseModel):
    id: UUID
    name: str
    email: str
    role: str


class TokenResponse(BaseModel):
    token: str
    user: UserData