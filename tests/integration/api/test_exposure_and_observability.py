"""Nada de mapa de rotas público, health separado e correlation id em todas as respostas."""
import pytest

from app.domain.enums.user import UserRole

from tests.integration.api.helpers import auth_header


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"])
def test_documentacao_nao_e_exposta_por_padrao(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert "ApoiaMais" not in response.text


def test_contrato_continua_exportavel_internamente():
    from main import app

    paths = app.openapi()["paths"]

    assert "/api/stages/{stage_id}/illustration" in paths
    assert "/health" not in paths and "/health/live" not in paths


def test_liveness_nao_depende_do_banco(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_verifica_o_banco(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_correlation_id_e_gerado_quando_ausente(client):
    response = client.get("/health/live")

    assert len(response.headers["x-correlation-id"]) == 32


def test_correlation_id_valido_e_propagado(client):
    response = client.get("/health/live", headers={"X-Correlation-ID": "jogo-abc.123"})

    assert response.headers["x-correlation-id"] == "jogo-abc.123"


@pytest.mark.parametrize("value", ["tem espaco", "x" * 65, "<script>", "a;b"])
def test_correlation_id_invalido_e_substituido(client, value):
    response = client.get("/health/live", headers={"X-Correlation-ID": value})

    assert response.headers["x-correlation-id"] != value
    assert len(response.headers["x-correlation-id"]) == 32


def test_correlation_id_tambem_em_erros(client):
    response = client.get("/api/users/", headers={"X-Correlation-ID": "erro-1"})

    assert response.status_code == 401
    assert response.headers["x-correlation-id"] == "erro-1"


def test_rate_limit_e_por_usuario_e_nao_por_ip(make_user):
    # no hospital, vários tablets saem pelo mesmo IP: um aluno não pode esgotar o limite do outro
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.api.dependencies import rate_limit as rl

    mini = FastAPI()

    @mini.get("/x", dependencies=[Depends(rl.rate_limit("teste-usuario", "2/minute"))])
    def x():
        return {}

    test_client = TestClient(mini)
    a = auth_header(make_user(UserRole.STUDENT))
    b = auth_header(make_user(UserRole.STUDENT))

    assert [test_client.get("/x", headers=a).status_code for _ in range(3)] == [200, 200, 429]
    assert test_client.get("/x", headers=b).status_code == 200
