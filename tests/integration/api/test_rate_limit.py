from app.api.dependencies.rate_limit import rate_limiter
from app.core.config import settings
from app.domain.enums.user import UserRole
from app.infrastructure.rate_limit import parse_rate

from tests.integration.api.helpers import auth_header


def _login(client, email="ninguem@example.com"):
    return client.post("/api/auth/login", json={"email": email, "password": "senha-errada"})


def test_login_bloqueia_apos_o_limite(client, repo):
    limit = parse_rate(settings.RATE_LIMIT_LOGIN).limit

    for _ in range(limit):
        assert _login(client).status_code == 401

    response = _login(client)

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    assert response.json()["success"] is False


def test_limite_de_login_vale_mesmo_trocando_o_email(client, repo):
    limit = parse_rate(settings.RATE_LIMIT_LOGIN).limit

    for i in range(limit):
        _login(client, email=f"tentativa{i}@example.com")

    assert _login(client, email="outro@example.com").status_code == 429


def test_login_bloqueado_nao_executa_o_use_case(client, make_user):
    student = make_user(UserRole.STUDENT)
    limit = parse_rate(settings.RATE_LIMIT_LOGIN).limit
    for _ in range(limit):
        _login(client)

    # mesmo com a senha certa, o limite vale
    response = client.post(
        "/api/auth/login", json={"email": student.email, "password": "senha-correta-123"}
    )

    assert response.status_code == 429


def test_cadastro_de_usuarios_tem_limite_proprio(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    headers = auth_header(teacher)
    limit = parse_rate(settings.RATE_LIMIT_USER_CREATION).limit

    for i in range(limit):
        response = client.post(
            "/api/users/students",
            json={"name": "Aluno", "email": f"aluno{i}@example.com", "password": "12345678"},
            headers=headers,
        )
        assert response.status_code == 201

    response = client.post(
        "/api/users/students",
        json={"name": "Aluno", "email": "extra@example.com", "password": "12345678"},
        headers=headers,
    )
    assert response.status_code == 429


def test_respostas_trazem_cabecalhos_de_limite(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.get("/api/users/", headers=auth_header(teacher))

    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"] == str(parse_rate(settings.RATE_LIMIT_DEFAULT).limit)
    assert "x-ratelimit-remaining" in response.headers


def test_limite_desligado_por_configuracao(client, repo, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    limit = parse_rate(settings.RATE_LIMIT_LOGIN).limit

    for _ in range(limit + 3):
        assert _login(client).status_code == 401


def test_reset_libera_novamente(client, repo):
    limit = parse_rate(settings.RATE_LIMIT_LOGIN).limit
    for _ in range(limit + 1):
        _login(client)

    rate_limiter.reset()

    assert _login(client).status_code == 401
