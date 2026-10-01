from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from main import app

from app.api.dependencies.use_cases import (
    get_create_user_usecase,
    get_get_user_usecase,
    get_update_user_usecase,
    get_delete_user_usecase,
    get_list_user_usecase,
)

from app.domain.enums.user import UserRole

from tests.integration.api.helpers import auth_header


def _mock_use_case(dependency, return_value=None):
    use_case = Mock()
    use_case.execute = AsyncMock(return_value=return_value)
    app.dependency_overrides[dependency] = lambda: use_case
    return use_case


def _user_dict(user_id, role="student", email="joao@example.com"):
    return {"id": str(user_id), "name": "João", "email": email, "role": role}


def test_create_student(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    user_id = uuid4()
    use_case = _mock_use_case(get_create_user_usecase, _user_dict(user_id))

    response = client.post(
        "/api/users/students",
        json={"name": "João", "email": "joao@example.com", "password": "12345678"},
        headers=auth_header(teacher),
    )

    assert response.status_code == 201
    assert response.json() == _user_dict(user_id)
    assert use_case.execute.await_args.kwargs["role"] == UserRole.STUDENT


def test_create_teacher(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    user_id = uuid4()
    use_case = _mock_use_case(get_create_user_usecase, _user_dict(user_id, role="teacher"))

    response = client.post(
        "/api/users/teachers",
        json={"name": "Maria", "email": "joao@example.com", "password": "12345678"},
        headers=auth_header(teacher),
    )

    assert response.status_code == 201
    assert response.json()["role"] == "teacher"
    assert use_case.execute.await_args.kwargs["role"] == UserRole.TEACHER


def test_list_users(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    users = [
        _user_dict(uuid4(), role="student", email="joao@example.com"),
        _user_dict(uuid4(), role="teacher", email="maria@example.com"),
    ]
    use_case = _mock_use_case(get_list_user_usecase, users)

    response = client.get("/api/users/", headers=auth_header(teacher))

    assert response.status_code == 200
    data = response.json()
    assert [u["role"] for u in data] == ["student", "teacher"]
    use_case.execute.assert_awaited_once()


def test_get_user(client, make_user):
    student = make_user(UserRole.STUDENT)
    use_case = _mock_use_case(get_get_user_usecase, _user_dict(student.id))

    response = client.get(f"/api/users/{student.id}", headers=auth_header(student))

    assert response.status_code == 200
    assert response.json()["id"] == str(student.id)
    use_case.execute.assert_awaited_once_with(student.id)


def test_update_user(client, make_user):
    student = make_user(UserRole.STUDENT)
    use_case = _mock_use_case(
        get_update_user_usecase,
        _user_dict(student.id, email="joao.novo@example.com"),
    )

    response = client.put(
        f"/api/users/{student.id}",
        json={"email": "joao.novo@example.com", "password": "87654321"},
        headers=auth_header(student),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "joao.novo@example.com"
    call_args = use_case.execute.await_args
    assert call_args.kwargs["user_id"] == student.id
    assert call_args.kwargs["request"].email == "joao.novo@example.com"
    assert call_args.kwargs["request"].password == "87654321"


def test_delete_user(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    user_id = uuid4()
    use_case = _mock_use_case(get_delete_user_usecase)

    response = client.delete(f"/api/users/{user_id}", headers=auth_header(teacher))

    assert response.status_code == 204
    assert response.content == b""
    use_case.execute.assert_awaited_once_with(user_id, deletable_roles={UserRole.STUDENT})


def test_cadastro_com_email_duplicado_retorna_409(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    existing = make_user(UserRole.STUDENT)

    response = client.post(
        "/api/users/students",
        json={"name": "Outro", "email": existing.email, "password": "12345678"},
        headers=auth_header(teacher),
    )

    assert response.status_code == 409
    assert response.json()["success"] is False


def test_login_fluxo_completo(client, make_user):
    student = make_user(UserRole.STUDENT)

    response = client.post(
        "/api/auth/login",
        json={"email": student.email, "password": "senha-correta-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "student"

    # o token emitido pelo login é aceito pelas rotas protegidas
    me = client.get(
        f"/api/users/{student.id}",
        headers={"Authorization": f"Bearer {body['token']}"},
    )
    assert me.status_code == 200


def test_login_nao_revela_se_o_email_existe(client, make_user):
    student = make_user(UserRole.STUDENT)

    senha_errada = client.post(
        "/api/auth/login", json={"email": student.email, "password": "senha-errada"}
    )
    email_inexistente = client.post(
        "/api/auth/login", json={"email": "ninguem@example.com", "password": "senha-errada"}
    )

    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()
