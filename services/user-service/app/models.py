from sqlalchemy import Column, String, Integer, ForeignKey, Date, Text
from .database import Base

class Responsavel(Base):
    __tablename__ = "Responsavel"
    id = Column(String(36), primary_key=True)
    nome = Column(String(255), nullable=False)

class Paciente(Base):
    __tablename__ = "Paciente"
    id = Column(String(36), primary_key=True)
    responsavel_id = Column(String(36), ForeignKey("Responsavel.id"))
    nome = Column(String(255), nullable=False)
    data_nascimento = Column(Date, nullable=False)
    nivel_atual = Column(Integer, default=1)
    notas_clinicas = Column(Text)