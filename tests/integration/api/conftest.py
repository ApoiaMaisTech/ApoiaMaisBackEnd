from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app

from app.api.dependencies.rate_limit import rate_limiter
from app.api.dependencies.repositories import get_user_repository
from app.api.dependencies.services import get_password_service
from app.domain.entities.user import User
from app.domain.enums.user import UserRole

from tests.integration.api.helpers import PASSWORD, InMemoryUserRepository


@pytest.fixture(autouse=True)
def _isolamento():
    rate_limiter.reset()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    rate_limiter.reset()


@pytest.fixture
def client():
    # raise_server_exceptions=False: queremos ver a resposta 500 do handler, não a exceção
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def repo():
    repository = InMemoryUserRepository()
    app.dependency_overrides[get_user_repository] = lambda: repository
    return repository


@pytest.fixture
def make_user(repo):
    password_hash = get_password_service().hash(PASSWORD)

    def _make(role: UserRole, email: str | None = None) -> User:
        user = User(
            id=uuid4(),
            name=f"Usuário {role.value}",
            email=email or f"{uuid4().hex[:8]}@example.com",
            password_hash=password_hash,
            role=role,
        )
        repo.users[user.id] = user
        return user

    return _make
