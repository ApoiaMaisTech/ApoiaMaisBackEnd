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
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "Recurso não encontrado."
    assert body["errors"] == []


def test_metodo_nao_permitido_retorna_405_padronizado(client):
    response = client.patch("/api/auth/login")

    assert response.status_code == 405
    assert response.json()["success"] is False


def test_uuid_invalido_na_rota_retorna_422(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.get("/api/users/123", headers=auth_header(teacher))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "exc,status,code,message",
    [
        (RuntimeError("segredo interno"), 500, "INTERNAL_ERROR", "Erro interno do servidor."),
        (OperationalError("SELECT 1", {}, Exception("conexão recusada")), 503, "SERVICE_UNAVAILABLE", "Serviço temporariamente indisponível."),
        (IntegrityError("INSERT", {}, Exception("Duplicate entry")), 409, "CONFLICT", "Conflito com dados existentes."),
    ],
    ids=["inesperado", "banco-fora", "integridade"],
)
def test_erros_de_infra_nao_vazam_detalhes(client, make_user, exc, status, code, message):
    teacher = make_user(UserRole.TEACHER)
    _list_use_case_raising(exc)

    response = client.get(
        "/api/users/", headers={**auth_header(teacher), "X-Correlation-ID": "infra-1"}
    )

    assert response.status_code == status
    assert response.json() == {
        "success": False,
        "code": code,
        "message": message,
        "errors": [],
        "correlation_id": "infra-1",
    }
    # inclusive no 500 (tratado fora do ExceptionMiddleware) o header continua lá
    assert response.headers["x-correlation-id"] == "infra-1"
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


# --- formato único de erro (issue #32) ---------------------------------------

from app.application.common.api_response import ErrorResponse  # noqa: E402

CAMPOS_DO_ERRO = {"success", "code", "message", "errors", "correlation_id"}


def _assert_formato_de_erro(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == CAMPOS_DO_ERRO
    ErrorResponse.model_validate(body)
    assert body["success"] is False
    assert body["code"] == code
    assert body["message"]
    assert body["correlation_id"] == response.headers["x-correlation-id"]
    return body


@pytest.mark.parametrize(
    "headers,code",
    [
        ({}, "UNAUTHORIZED"),
        ({"Authorization": "Bearer nao-e-um-jwt"}, "TOKEN_INVALID"),
    ],
    ids=["sem-token", "token-invalido"],
)
def test_401_tem_codigo_especifico(client, repo, headers, code):
    _assert_formato_de_erro(client.get("/api/users/", headers=headers), 401, code)


def test_token_expirado_tem_codigo_proprio(client, repo):
    from uuid import uuid4

    from tests.integration.api.helpers import forge_token

    headers = forge_token({"user_id": str(uuid4()), "role": "teacher", "exp": 1})

    _assert_formato_de_erro(client.get("/api/users/", headers=headers), 401, "TOKEN_EXPIRED")


def test_403_por_perfil(client, make_user):
    student = make_user(UserRole.STUDENT)

    _assert_formato_de_erro(client.get("/api/users/", headers=auth_header(student)), 403, "FORBIDDEN")


def test_409_email_duplicado(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    existente = make_user(UserRole.STUDENT, email="ja.existe@example.com")

    response = client.post(
        "/api/users/students",
        json={"name": "Outra Pessoa", "email": existente.email, "password": "senha-nova-123"},
        headers=auth_header(teacher),
    )

    _assert_formato_de_erro(response, 409, "EMAIL_ALREADY_EXISTS")


def test_422_validacao_lista_os_campos(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.post(
        "/api/users/students",
        json={"email": "x@example.com"},
        headers=auth_header(teacher),
    )

    body = _assert_formato_de_erro(response, 422, "VALIDATION_ERROR")
    assert {e.split(":")[0] for e in body["errors"]} == {"name", "password"}


def test_json_malformado_diz_que_e_json(client, repo):
    response = client.post(
        "/api/auth/login",
        content="{nao é json",
        headers={"Content-Type": "application/json"},
    )

    body = _assert_formato_de_erro(response, 422, "VALIDATION_ERROR")
    assert any("JSON malformado" in e for e in body["errors"])


def test_404_e_405_do_framework_no_mesmo_formato(client):
    _assert_formato_de_erro(client.get("/api/nao-existe"), 404, "NOT_FOUND")
    _assert_formato_de_erro(client.patch("/api/auth/login"), 405, "METHOD_NOT_ALLOWED")


def test_429_tem_codigo_e_retry_after(client, make_user, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "a@example.com", "password": "x"})

    response = client.post("/api/auth/login", json={"email": "a@example.com", "password": "x"})

    _assert_formato_de_erro(response, 429, "RATE_LIMITED")
    assert int(response.headers["retry-after"]) > 0


def test_500_tem_codigo_e_correlation_id(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    _list_use_case_raising(RuntimeError("boom"))

    _assert_formato_de_erro(client.get("/api/users/", headers=auth_header(teacher)), 500, "INTERNAL_ERROR")


def test_contrato_openapi_documenta_o_formato_de_erro():
    schema = app.openapi()
    assert "ErrorResponse" in schema["components"]["schemas"]
    # o 422 padrão do FastAPI ({"detail": [...]}) não descreve a resposta real
    assert "HTTPValidationError" not in schema["components"]["schemas"]

    ref = {"$ref": "#/components/schemas/ErrorResponse"}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            for status_code in ("422", "429", "500"):
                content = operation["responses"][status_code]["content"]["application/json"]
                assert content["schema"] == ref, f"{method.upper()} {path} {status_code}"
            if path.startswith("/api/users") or path.startswith("/api/ai-images") or "/stages/" in path:
                assert "401" in operation["responses"], f"{method.upper()} {path} sem 401"
                assert "403" in operation["responses"], f"{method.upper()} {path} sem 403"
