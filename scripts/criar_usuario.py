"""Cria um usuário direto no banco, sem passar pela API.

Serve para o primeiro professor (as rotas de cadastro exigem um professor
autenticado) e para os usuários de teste do ambiente local.

Uso (na raiz do backend ou no container):
    python -m scripts.criar_usuario --role teacher --nome "Professor" --email p@x.dev --senha "..."

Se o email já existir, não faz nada e sai com código 0.
"""

import argparse
import asyncio
import sys

from app.api.dependencies.services import get_password_service
from app.application.dto.create_user_request import CreateUserRequest
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.domain.enums.user import UserRole
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.infrastructure.database.repositories.sql_user_repository import SqlUserRepository
from app.infrastructure.database.session import AsyncSessionLocal


async def criar(role: UserRole, nome: str, email: str, senha: str) -> None:
    request = CreateUserRequest(name=nome, email=email, password=senha)
    async with AsyncSessionLocal() as session:
        use_case = CreateUserUseCase(
            repository=SqlUserRepository(db_session=session),
            password_service=get_password_service(),
        )
        try:
            user = await use_case.execute(request=request, role=role)
        except EmailAlreadyExistsException:
            print(f"{email} já existe, nada a fazer.")
            return
    print(f"Criado {role.value} {user.email} ({user.id}).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--role", choices=[UserRole.TEACHER.value, UserRole.STUDENT.value], required=True)
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", required=True)
    args = parser.parse_args()

    try:
        asyncio.run(criar(UserRole(args.role), args.nome, args.email, args.senha))
    except ValueError as exc:
        # validação do CreateUserRequest (email, tamanho de senha/nome)
        sys.exit(f"Dados inválidos: {exc}")


if __name__ == "__main__":
    main()
