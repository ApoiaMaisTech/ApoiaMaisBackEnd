### DEPENDENCIAS DA API PARA O BANCO DE DADOS ###
from infrastructure.database.session import AsyncSessionLocal
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

from infrastructure.database.repositories.sql_user_repository import SqlUserRepository
def get_user_repository() -> SqlUserRepository:
    return SqlUserRepository(db_session=AsyncSessionLocal())

