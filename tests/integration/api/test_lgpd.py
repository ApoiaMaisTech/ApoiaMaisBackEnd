"""LGPD na API: o que vai para logs, tokens e respostas."""
import base64
import io
import json
import logging

import pytest

from app.core.logging import build_formatter
from app.domain.enums.user import UserRole

from tests.integration.api.helpers import PASSWORD, auth_header


def _jwt_payload(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def test_token_nao_carrega_email_nem_nome(client, make_user):
    student = make_user(UserRole.STUDENT, email="crianca.responsavel@example.com")

    response = client.post("/api/auth/login", json={"email": student.email, "password": PASSWORD})

    assert response.status_code == 200
    payload = _jwt_payload(response.json()["token"])
    assert set(payload) == {"user_id", "role", "iat", "exp"}
    assert student.email not in json.dumps(payload)


@pytest.fixture
def logs():
    """Captura a saída real dos logs (mesmo formatter da aplicação), em JSON."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(build_formatter(json_logs=True))
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    yield stream
    root.removeHandler(handler)
    root.setLevel(previous_level)


def test_log_de_acesso_nao_tem_corpo_nem_query_string(client, make_user, logs):
    teacher = make_user(UserRole.TEACHER)
    email = "novo.aluno@example.com"

    client.post(
        "/api/users/students?origem=" + email,
        json={"name": "Novo Aluno", "email": email, "password": "senha-secreta-123"},
        headers=auth_header(teacher),
    )

    output = logs.getvalue()
    access = [json.loads(line) for line in output.splitlines() if '"apoiamais.access"' in line]
    assert access, "sem log de acesso"
    assert access[-1]["path"] == "/api/users/students"
    assert email not in output
    assert "senha-secreta-123" not in output


def test_login_com_erro_nao_loga_email_nem_senha(client, repo, logs):
    client.post("/api/auth/login", json={"email": "alguem@example.com", "password": "senha-errada-999"})

    output = logs.getvalue()
    assert output, "nenhum log capturado"
    assert "alguem@example.com" not in output
    assert "senha-errada-999" not in output


def test_erro_500_com_dado_pessoal_na_excecao_sai_limpo_no_log(client, make_user, logs):
    from unittest.mock import AsyncMock, Mock

    from main import app
    from app.api.dependencies.use_cases import get_list_user_usecase

    teacher = make_user(UserRole.TEACHER)
    use_case = Mock()
    use_case.execute = AsyncMock(side_effect=RuntimeError("falhou para joana.souza@example.com"))
    app.dependency_overrides[get_list_user_usecase] = lambda: use_case

    response = client.get("/api/users/", headers=auth_header(teacher))

    assert response.status_code == 500
    output = logs.getvalue()
    assert "RuntimeError" in output
    assert "joana.souza@example.com" not in output and "[email]" in output


def test_engine_nao_coloca_parametros_nas_mensagens_de_erro():
    from app.infrastructure.database.session import engine

    assert engine.sync_engine.hide_parameters is True
