from pydantic import BaseModel, EmailStr, Field

# basemodel que define o formato da requisicao de criacao de usarios, independente de qual seja o cargo
class CreateUserRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
