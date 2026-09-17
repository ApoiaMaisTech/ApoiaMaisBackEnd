from uuid import uuid4

import pytest

from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)


@pytest.mark.asyncio
async def test_list_users(db_session):
    repository = SqlUserRepository(db_session)

    user1 = User(
        id=uuid4(),
        name="Usuário Lista 1",
        email=f"lista1_{uuid4()}@example.com",
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    user2 = User(
        id=uuid4(),
        name="Usuário Lista 2",
        email=f"lista2_{uuid4()}@example.com",
        password_hash="hashed_password",
        role=UserRole.TEACHER,
    )

    await repository.create(user1)
    await repository.create(user2)

    users = await repository.list()

    ids = [user.id for user in users]

    assert user1.id in ids
    assert user2.id in ids


@pytest.mark.asyncio
async def test_update_user(db_session):
    repository = SqlUserRepository(db_session)

    user = User(
        id=uuid4(),
        name="Usuário Original",
        email=f"update_{uuid4()}@example.com",
        password_hash="old_password",
        role=UserRole.STUDENT,
    )

    await repository.create(user)

    updated_user = User(
        id=user.id,
        name="Usuário Atualizado",
        email=user.email,
        password_hash="new_password",
        role=UserRole.TEACHER,
    )

    result = await repository.update(updated_user)

    assert result.id == user.id
    assert result.name == "Usuário Atualizado"
    assert result.email == user.email
    assert result.password_hash == "new_password"
    assert result.role == UserRole.TEACHER

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.name == "Usuário Atualizado"
    assert found_user.password_hash == "new_password"
    assert found_user.role == UserRole.TEACHER


@pytest.mark.asyncio
async def test_delete_user(db_session):
    repository = SqlUserRepository(db_session)

    user = User(
        id=uuid4(),
        name="Usuário Para Deletar",
        email=f"delete_{uuid4()}@example.com",
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    await repository.create(user)

    found_before_delete = await repository.get_by_id(user.id)

    assert found_before_delete is not None

    await repository.delete(user.id)

    found_after_delete = await repository.get_by_id(user.id)

    assert found_after_delete is None