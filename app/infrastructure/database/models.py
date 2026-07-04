from sqlalchemy import Column, String, Boolean, Enum
from infrastructure.database import Base

class Usuario(Base):
    __tablename__ = "Usuario"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)

    cargo = Column(Enum('professor', 'medico', 'administrador', name="cargo_enum"), default='professor', nullable=False)
    esta_ativo = Column(Boolean, default=True, nullable=False)
    



