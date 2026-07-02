from uuid import UUID
from domain.enums.user import UserRole

# objeto para regra de negocios
class User:
    id: UUID
    name: str
    email: str
    password_hash: str
    role: UserRole
