from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.infrastructure.database.repositories.sql_user_repository import (
    SqlUserRepository,
)


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_nonexistent_user(db_session):
    repository = SqlUserRepository(db_session)

    result = await repository.get_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_email_returns_none_for_nonexistent_user(db_session):
    repository = SqlUserRepository(db_session)

    result = await repository.get_by_email(
        f"nonexistent_{uuid4()}@example.com"
    )

    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_user_does_not_raise_error(db_session):
    repository = SqlUserRepository(db_session)

    await repository.delete(uuid4())


@pytest.mark.asyncio
async def test_create_user_with_duplicate_email_raises_integrity_error(
    db_session,
):
    repository = SqlUserRepository(db_session)

    email = f"duplicate_{uuid4()}@example.com"

    user1 = User(
        id=uuid4(),
        name="Primeiro Usuário",
        email=email,
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    user2 = User(
        id=uuid4(),
        name="Segundo Usuário",
        email=email,
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    await repository.create(user1)

    with pytest.raises(IntegrityError):
        await repository.create(user2)