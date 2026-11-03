from pydantic import BaseModel

from app.application.dto.validators import Email, NewPassword, PersonName


# formato da requisicao de criacao de usuarios, independente do cargo.
# O cargo vem da rota (/students, /teachers), nunca do corpo: um "role" enviado é ignorado.
class CreateUserRequest(BaseModel):
    name: PersonName
    email: Email
    password: NewPassword
