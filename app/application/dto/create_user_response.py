from pydantic import BaseModel, EmailStr
from uuid import UUID

# importa enum que define cargo do usuario
from app.domain.enums.user import UserRole

# basemodel de resposta da requisicao mostrando o cargo do usuario
class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
