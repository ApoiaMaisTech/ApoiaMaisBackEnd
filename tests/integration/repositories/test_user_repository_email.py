from uuid import uuid4

import pytest

from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)


@pytest.mark.asyncio
async def test_get_user_by_email(db_session):
    repository = SqlUserRepository(db_session)

    email = f"email_{uuid4()}@example.com"

    user = User(
        id=uuid4(),
        name="Teste Email",
        email=email,
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    await repository.create(user)

    found_user = await repository.get_by_email(email)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == email
    assert found_user.name == "Teste Email"
    assert found_user.role == UserRole.STUDENT