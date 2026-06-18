from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    nome: str
    class Config:
        from_attributes = True