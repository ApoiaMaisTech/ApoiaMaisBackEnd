from uuid import uuid4

import pytest

from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)


@pytest.mark.asyncio
async def test_create_and_get_user(db_session):
    repository = SqlUserRepository(db_session)

    user = User(
        id=uuid4(),
        name="Teste Integração",
        email=f"teste_{uuid4()}@example.com",
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    created_user = await repository.create(user)

    assert created_user.id == user.id
    assert created_user.name == user.name
    assert created_user.email == user.email
    assert created_user.role == UserRole.STUDENT

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == user.email
    assert found_user.role == UserRole.STUDENT
