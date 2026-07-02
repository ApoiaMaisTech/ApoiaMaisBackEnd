from pydantic import BaseModel, EmailStr

class UpdateUserRequest(BaseModel):
    email: EmailStr
    password: str

