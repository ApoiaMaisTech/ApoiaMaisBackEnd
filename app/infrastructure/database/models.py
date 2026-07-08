import uuid
from sqlalchemy import Column, String, Boolean, Enum
from app.infrastructure.database import Base

class Usuario(Base):
    __tablename__ = "Usuario"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)

    cargo = Column(Enum('teacher', 'medico', 'administrador', 'student'), name="cargo_enum", default='teacher', nullable=False)
    esta_ativo = Column(Boolean, default=True, nullable=False)


