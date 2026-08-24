from uuid import UUID
from dataclasses import dataclass  
from app.domain.enums.user import UserRole

# objeto para regra de negocios
@dataclass
class User:
    id: UUID | None 
    name: str
    email: str
    password_hash: str
    role: UserRole
