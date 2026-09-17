from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from main import app

from app.api.dependencies.use_cases import (
    get_create_user_usecase,
    get_get_user_usecase,
    get_update_user_usecase,
    get_delete_user_usecase,
    get_list_user_usecase,
)

from app.api.dependencies.auth import get_current_teacher

from app.domain.entities.user import User
from app.domain.enums.user import UserRole


client = TestClient(app)


def test_create_student():
    user_id = uuid4()

    created_user = User(
        id=user_id,
        name="João",
        email="joao@example.com",
        password_hash="hashed_password",
        role=UserRole.STUDENT,
    )

    use_case = Mock()
    use_case.execute = AsyncMock(
        return_value={
            "id": str(created_user.id),
            "name": created_user.name,
            "email": created_user.email,
            "role": created_user.role,
        }
    )

    app.dependency_overrides[
        get_create_user_usecase
    ] = lambda: use_case

    response = client.post(
        "/api/users/students",
        json={
            "name": "João",
            "email": "joao@example.com",
            "password": "12345678",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user_id)
    assert data["name"] == "João"
    assert data["email"] == "joao@example.com"
    assert data["role"] == "student"

    use_case.execute.assert_awaited_once()


def test_create_teacher():
    user_id = uuid4()

    created_user = User(
        id=user_id,
        name="Maria",
        email="maria@example.com",
        password_hash="hashed_password",
        role=UserRole.TEACHER,
    )

    use_case = Mock()
    use_case.execute = AsyncMock(
        return_value={
            "id": str(created_user.id),
            "name": created_user.name,
            "email": created_user.email,
            "role": created_user.role,
        }
    )

    app.dependency_overrides[
        get_create_user_usecase
    ] = lambda: use_case

    response = client.post(
        "/api/users/teachers",
        json={
            "name": "Maria",
            "email": "maria@example.com",
            "password": "12345678",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user_id)
    assert data["name"] == "Maria"
    assert data["email"] == "maria@example.com"
    assert data["role"] == "teacher"

    use_case.execute.assert_awaited_once()


def test_list_users():
    users = [
        {
            "id": str(uuid4()),
            "name": "João",
            "email": "joao@example.com",
            "role": "student",
        },
        {
            "id": str(uuid4()),
            "name": "Maria",
            "email": "maria@example.com",
            "role": "teacher",
        },
    ]

    use_case = Mock()
    use_case.execute = AsyncMock(return_value=users)

    app.dependency_overrides[
        get_list_user_usecase
    ] = lambda: use_case

    app.dependency_overrides[
        get_current_teacher
    ] = lambda: {
        "id": uuid4(),
        "email": "professor@example.com",
        "role": UserRole.TEACHER.value,
    }

    response = client.get("/api/users/")

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["name"] == "João"
    assert data[0]["role"] == "student"
    assert data[1]["name"] == "Maria"
    assert data[1]["role"] == "teacher"

    use_case.execute.assert_awaited_once()

def test_get_user():
    user_id = uuid4()

    user = {
        "id": str(user_id),
        "name": "João",
        "email": "joao@example.com",
        "role": "student",
    }

    use_case = Mock()
    use_case.execute = AsyncMock(return_value=user)

    app.dependency_overrides[
        get_get_user_usecase
    ] = lambda: use_case

    response = client.get(f"/api/users/{user_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user_id)
    assert data["name"] == "João"
    assert data["email"] == "joao@example.com"
    assert data["role"] == "student"

    use_case.execute.assert_awaited_once_with(user_id)

def test_update_user():
    user_id = uuid4()

    updated_user = {
        "id": str(user_id),
        "name": "João",
        "email": "joao.novo@example.com",
        "role": "student",
    }

    use_case = Mock()
    use_case.execute = AsyncMock(return_value=updated_user)

    app.dependency_overrides[
        get_update_user_usecase
    ] = lambda: use_case

    response = client.put(
        f"/api/users/{user_id}",
        json={
            "email": "joao.novo@example.com",
            "password": "87654321",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user_id)
    assert data["email"] == "joao.novo@example.com"
    assert data["role"] == "student"

    use_case.execute.assert_awaited_once()

    call_args = use_case.execute.await_args

    assert call_args.kwargs["user_id"] == user_id
    assert call_args.kwargs["request"].email == "joao.novo@example.com"
    assert call_args.kwargs["request"].password == "87654321"

def test_delete_user():
    user_id = uuid4()

    use_case = Mock()
    use_case.execute = AsyncMock(return_value=None)

    app.dependency_overrides[
        get_delete_user_usecase
    ] = lambda: use_case

    response = client.delete(f"/api/users/{user_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""

    use_case.execute.assert_awaited_once_with(user_id)