# importacao do enum q contem os cargos e do dto
from application.dto.create_user_request import CreateUserRequest
from domain.enums.user import UserRole


class CreateUserUseCase:
    def __init__(self,repository,password_service):
        self.repository = repository
        self.password_service = password_service

    async def execute(self,request: CreateUserRequest, role: UserRole):
        pass 