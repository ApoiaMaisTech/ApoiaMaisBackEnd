from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from main import app

from app.api.dependencies.use_cases import get_list_user_usecase
from app.domain.enums.user import UserRole

from tests.integration.api.helpers import auth_header


def _list_use_case_raising(exc: Exception):
    use_case = Mock()
    use_case.execute = AsyncMock(side_effect=exc)
    app.dependency_overrides[get_list_user_usecase] = lambda: use_case


def test_validacao_retorna_422_padronizado_sem_ecoar_a_senha(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.post(
        "/api/users/students",
        json={"name": "Jo", "email": "nao-e-email", "password": "curta"},
        headers=auth_header(teacher),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Dados inválidos."
    campos = {erro.split(":")[0] for erro in body["errors"]}
    assert campos == {"name", "email", "password"}
    assert "curta" not in response.text


def test_json_malformado_retorna_422(client, repo):
    response = client.post(
        "/api/auth/login",
        content="{nao é json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_rota_inexistente_retorna_404_padronizado(client):
    response = client.get("/api/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"success": False, "message": "Not Found", "errors": []}


def test_metodo_nao_permitido_retorna_405_padronizado(client):
    response = client.patch("/api/auth/login")

    assert response.status_code == 405
    assert response.json()["success"] is False


def test_uuid_invalido_na_rota_retorna_422(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.get("/api/users/123", headers=auth_header(teacher))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "exc,status,message",
    [
        (RuntimeError("segredo interno"), 500, "Erro interno do servidor."),
        (OperationalError("SELECT 1", {}, Exception("conexão recusada")), 503, "Serviço temporariamente indisponível."),
        (IntegrityError("INSERT", {}, Exception("Duplicate entry")), 409, "Conflito com dados existentes."),
    ],
    ids=["inesperado", "banco-fora", "integridade"],
)
def test_erros_de_infra_nao_vazam_detalhes(client, make_user, exc, status, message):
    teacher = make_user(UserRole.TEACHER)
    _list_use_case_raising(exc)

    response = client.get("/api/users/", headers=auth_header(teacher))

    assert response.status_code == status
    assert response.json() == {"success": False, "message": message, "errors": []}
    for vazamento in ("segredo interno", "conexão recusada", "Duplicate entry", "Traceback"):
        assert vazamento not in response.text


def test_health_retorna_503_sem_banco(client, monkeypatch):
    import main

    class SessaoQuebrada:
        async def __aenter__(self):
            raise OperationalError("SELECT 1", {}, Exception("sem banco"))

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(main, "AsyncSessionLocal", SessaoQuebrada)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
