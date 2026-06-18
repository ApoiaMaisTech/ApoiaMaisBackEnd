from pydantic import BaseModel
from typing import Optional, List
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    password: str
    nome: str

    @validator('password')
    def password_length(cls, v):
        if len(v) > 72:
            return v[:72] 
        return v

class PacienteBase(BaseModel):
    nome: str
    data_nascimento: str
    notas_clinicas: Optional[str] = None

class PacienteCreate(PacienteBase):
    responsavel_id: str

class Paciente(PacienteBase):
    id: str
    nivel_atual: int
    experiencia_total: int
    
    class Config:
        from_attributes = True