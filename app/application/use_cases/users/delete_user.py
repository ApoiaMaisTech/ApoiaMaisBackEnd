from domain.repositories.user_repository import UserRepository
from domain.exceptions.user_not_found import UserNotFoundException


class DeleteUserUseCase:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def execute(self, user_id: int):

        user = await self.repository.get_by_id(user_id)

        if not user:
            raise UserNotFoundException("User not found")

        await self.repository.delete(user_id)

        return {"message": "User deleted successfully"}