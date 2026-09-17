from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest

from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.update_user_request import UpdateUserRequest
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.application.use_cases.users.get_user_usecase import GetUserUseCase
from app.application.use_cases.users.list_user_usecase import ListUserUseCase
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
from app.application.use_cases.users.delete_user_usecase import DeleteUserUseCase

from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.domain.exceptions.email_already_exists import EmailAlreadyExistsException
from app.domain.exceptions.user_not_found import UserNotFoundException


@pytest.mark.asyncio
async def test_create_user_success():
    repository = Mock()
    repository.get_by_email = AsyncMock(return_value=None)

    created_user = User(
        id=uuid4(),
        name="João",
        email="joao@example.com",
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    repository.create = AsyncMock(return_value=created_user)

    password_service = Mock()
    password_service.hash.return_value = "hashed_password"

    use_case = CreateUserUseCase(repository, password_service)

    request = CreateUserRequest(
        name="João",
        email="joao@example.com",
        password="12345678",
    )

    result = await use_case.execute(request, UserRole.STUDENT)

    assert result.id == created_user.id
    assert result.name == "João"
    assert result.email == "joao@example.com"
    assert result.role == UserRole.STUDENT

    repository.get_by_email.assert_awaited_once_with("joao@example.com")
    password_service.hash.assert_called_once_with("12345678")
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_with_existing_email():
    repository = Mock()

    existing_user = User(
        id=uuid4(),
        name="Usuário Existente",
        email="existing@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )

    repository.get_by_email = AsyncMock(return_value=existing_user)
    repository.create = AsyncMock()

    password_service = Mock()

    use_case = CreateUserUseCase(repository, password_service)

    request = CreateUserRequest(
        name="Novo Usuário",
        email="existing@example.com",
        password="12345678",
    )

    with pytest.raises(EmailAlreadyExistsException):
        await use_case.execute(request, UserRole.STUDENT)

    repository.create.assert_not_awaited()
    password_service.hash.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_success():
    repository = Mock()

    user = User(
        id=uuid4(),
        name="Maria",
        email="maria@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )

    repository.get_by_id = AsyncMock(return_value=user)

    use_case = GetUserUseCase(repository)

    result = await use_case.execute(user.id)

    assert result.id == user.id
    assert result.name == "Maria"
    assert result.email == "maria@example.com"
    assert result.role == UserRole.STUDENT

    repository.get_by_id.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_get_user_not_found():
    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=None)

    use_case = GetUserUseCase(repository)

    user_id = uuid4()

    with pytest.raises(UserNotFoundException):
        await use_case.execute(user_id)

    repository.get_by_id.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_list_users_success():
    repository = Mock()

    user1 = User(
        id=uuid4(),
        name="João",
        email="joao@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )

    user2 = User(
        id=uuid4(),
        name="Maria",
        email="maria@example.com",
        password_hash="hashed",
        role=UserRole.TEACHER,
    )

    repository.list = AsyncMock(return_value=[user1, user2])

    use_case = ListUserUseCase(repository)

    result = await use_case.execute()

    assert len(result) == 2
    assert result[0].id == user1.id
    assert result[0].name == "João"
    assert result[1].id == user2.id
    assert result[1].name == "Maria"

    repository.list.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_users_empty():
    repository = Mock()
    repository.list = AsyncMock(return_value=[])

    use_case = ListUserUseCase(repository)

    result = await use_case.execute()

    assert result == []

    repository.list.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_success():
    repository = Mock()

    user = User(
        id=uuid4(),
        name="João",
        email="old@example.com",
        password_hash="old_hash",
        role=UserRole.STUDENT,
    )

    updated_user = User(
        id=user.id,
        name="João",
        email="new@example.com",
        password_hash="new_hash",
        role=UserRole.STUDENT,
    )

    repository.get_by_id = AsyncMock(return_value=user)
    repository.get_by_email = AsyncMock(return_value=None)
    repository.update = AsyncMock(return_value=updated_user)

    password_service = Mock()
    password_service.hash.return_value = "new_hash"

    use_case = UpdateUserUseCase(repository, password_service)

    request = UpdateUserRequest(
        email="new@example.com",
        password="new_password",
    )

    result = await use_case.execute(user.id, request)

    assert result.id == user.id
    assert result.email == "new@example.com"

    password_service.hash.assert_called_once_with("new_password")
    repository.update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update_user_not_found():
    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=None)

    repository.get_by_email = AsyncMock()
    repository.update = AsyncMock()

    password_service = Mock()

    use_case = UpdateUserUseCase(repository, password_service)

    user_id = uuid4()

    request = UpdateUserRequest(
        email="new@example.com",
        password="new_password",
    )

    with pytest.raises(UserNotFoundException):
        await use_case.execute(user_id, request)

    repository.get_by_email.assert_not_awaited()
    repository.update.assert_not_awaited()
    password_service.hash.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_with_existing_email():
    repository = Mock()

    user = User(
        id=uuid4(),
        name="João",
        email="old@example.com",
        password_hash="old_hash",
        role=UserRole.STUDENT,
    )

    other_user = User(
        id=uuid4(),
        name="Maria",
        email="new@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )

    repository.get_by_id = AsyncMock(return_value=user)
    repository.get_by_email = AsyncMock(return_value=other_user)
    repository.update = AsyncMock()

    password_service = Mock()

    use_case = UpdateUserUseCase(repository, password_service)

    request = UpdateUserRequest(
        email="new@example.com",
        password="new_password",
    )

    with pytest.raises(EmailAlreadyExistsException):
        await use_case.execute(user.id, request)

    repository.update.assert_not_awaited()
    password_service.hash.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_success():
    repository = Mock()

    user = User(
        id=uuid4(),
        name="João",
        email="joao@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )

    repository.get_by_id = AsyncMock(return_value=user)
    repository.delete = AsyncMock()

    use_case = DeleteUserUseCase(repository)

    result = await use_case.execute(user.id)

    assert result.id == user.id
    assert result.name == user.name
    assert result.email == user.email
    assert result.role == user.role

    repository.get_by_id.assert_awaited_once_with(user.id)
    repository.delete.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_delete_user_not_found():
    repository = Mock()

    repository.get_by_id = AsyncMock(return_value=None)
    repository.delete = AsyncMock()

    use_case = DeleteUserUseCase(repository)

    user_id = uuid4()

    with pytest.raises(UserNotFoundException):
        await use_case.execute(user_id)

    repository.delete.assert_not_awaited()
