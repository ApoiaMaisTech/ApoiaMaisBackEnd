from pydantic import BaseModel

from app.application.dto.validators import Email, NewPassword


# só email e senha podem mudar; nome, cargo e id enviados no corpo são ignorados
class UpdateUserRequest(BaseModel):
    email: Email
    password: NewPassword
