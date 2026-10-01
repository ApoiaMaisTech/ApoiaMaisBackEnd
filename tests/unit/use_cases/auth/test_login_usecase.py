from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest

from app.application.dto.login_request import LoginRequest
from app.application.use_cases.auth.login_usecase import LoginUseCase
from app.domain.entities.user import User
from app.domain.enums.user import UserRole
from app.domain.exceptions.invalid_credentials import InvalidCredentialsException


def _use_case(user, senha_confere=True):
    repository = Mock()
    repository.get_by_email = AsyncMock(return_value=user)
    password_service = Mock()
    password_service.verify = Mock(return_value=senha_confere)
    jwt_service = Mock()
    jwt_service.generate_token = Mock(return_value="token")
    return LoginUseCase(repository, password_service, jwt_service), jwt_service


def _user():
    return User(
        id=uuid4(),
        name="João",
        email="joao@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT,
    )


@pytest.mark.asyncio
async def test_login_success():
    user = _user()
    use_case, jwt_service = _use_case(user)

    result = await use_case.execute(LoginRequest(email=user.email, password="senha"))

    assert result.token == "token"
    assert result.user.role == "student"
    jwt_service.generate_token.assert_called_once_with(user.id, user.email, user.role)


@pytest.mark.asyncio
async def test_login_email_inexistente_e_credencial_invalida():
    use_case, jwt_service = _use_case(None)

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(LoginRequest(email="x@example.com", password="senha"))

    jwt_service.generate_token.assert_not_called()


@pytest.mark.asyncio
async def test_login_senha_errada():
    use_case, jwt_service = _use_case(_user(), senha_confere=False)

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(LoginRequest(email="joao@example.com", password="errada"))

    jwt_service.generate_token.assert_not_called()
