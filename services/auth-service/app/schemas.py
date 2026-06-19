from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    
    password: str = Field(..., max_length=72)
    cargo: str = Field(default="aluno")

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    nome: str
    cargo: str 

    class Config:
        from_attributes = True