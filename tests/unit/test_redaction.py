"""LGPD: dados pessoais e segredos não saem do processo em logs nem em texto de erro."""
import io
import json
import logging

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.logging import build_formatter
from app.core.redaction import REDACTED, redact, redact_text, safe_error_text

EMAIL = "maria.silva@example.com"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMSJ9.c2lnbmF0dXJhLWZhbHNh"
HASH = "pbkdf2_sha256$600000$c2FsdA$aGFzaA"


@pytest.mark.parametrize(
    "text,leak,marker",
    [
        (f"usuário {EMAIL} não encontrado", EMAIL, "[email]"),
        (f"Authorization: Bearer {JWT}", JWT, "Bearer [redacted]"),
        (f"token={JWT}", JWT, "[jwt]"),
        (f"hash {HASH} inválido", HASH, "[hash]"),
        ("cpf 123.456.789-09 duplicado", "123.456.789-09", "[cpf]"),
        ("hash " + "ab" * 16 + "$" + "cd" * 32 + " salvo", "cd" * 32, "[hash]"),
    ],
    ids=["email", "bearer", "jwt", "hash-de-senha", "cpf", "hash-do-projeto"],
)
def test_texto_livre_e_limpo(text, leak, marker):
    cleaned = redact_text(text)

    assert leak not in cleaned
    assert marker in cleaned


def test_parametros_de_sql_do_sqlalchemy_sao_removidos():
    exc = IntegrityError(
        "INSERT INTO user (id, email, password_hash, name) VALUES (%s, %s, %s, %s)",
        ("ab12", EMAIL, HASH, "Maria Silva"),
        Exception("(1062, \"Duplicate entry 'x' for key 'user.ix_user_email'\")"),
    )

    cleaned = safe_error_text(exc, 1000)

    assert "Maria Silva" not in cleaned and EMAIL not in cleaned and HASH not in cleaned
    assert "[parameters: [redacted]]" in cleaned
    # o resto continua útil para diagnóstico
    assert "IntegrityError" in cleaned and "INSERT INTO user" in cleaned


@pytest.mark.parametrize(
    "key",
    ["password", "senha", "new_password", "token", "access_token", "Authorization", "cookie",
     "email", "user_email", "cpf", "phone", "telefone", "birth_date", "data_nascimento",
     "clinical_rate", "diagnostico", "OPENAI_API_KEY", "jwt_secret"],
)
def test_campos_sensiveis_sao_mascarados(key):
    assert redact({key: "valor"}) == {key: REDACTED}


@pytest.mark.parametrize("key", ["event", "logger", "level", "correlation_id", "event_id", "method", "path", "status", "queue"])
def test_campos_de_diagnostico_continuam(key):
    assert redact({key: "valor"}) == {key: "valor"}


def test_estruturas_aninhadas_e_original_intacto():
    data = {"user": {"id": "1", "email": EMAIL, "tags": [f"contato {EMAIL}"]}}

    cleaned = redact(data)

    assert cleaned == {"user": {"id": "1", "email": REDACTED, "tags": ["contato [email]"]}}
    assert data["user"]["email"] == EMAIL


def _log_through_pipeline(emit) -> str:
    """Passa um log pelo mesmo formatter da aplicação e devolve a saída JSON."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(build_formatter(json_logs=True))
    logger = logging.getLogger(f"teste.lgpd.{id(stream)}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    emit(logger)
    return stream.getvalue()


def test_traceback_de_erro_de_banco_sai_sem_dados_pessoais():
    def emit(logger):
        try:
            raise OperationalError(
                "UPDATE user SET email=%s, password_hash=%s WHERE id=%s",
                (EMAIL, HASH, "ab12"),
                Exception("Lost connection"),
            )
        except OperationalError:
            logger.exception("Erro de banco em PUT /api/users/ab12")

    output = _log_through_pipeline(emit)

    record = json.loads(output)
    assert "exception" in record and "OperationalError" in record["exception"]
    assert EMAIL not in output and HASH not in output


def test_extra_com_campos_sensiveis_e_mascarado():
    output = _log_through_pipeline(
        lambda logger: logger.info(
            "login", extra={"email": EMAIL, "password": "segredo123", "authorization": f"Bearer {JWT}", "path": "/api/auth/login"}
        )
    )

    record = json.loads(output)
    assert record["email"] == record["password"] == record["authorization"] == REDACTED
    assert record["path"] == "/api/auth/login"
    assert "segredo123" not in output and EMAIL not in output and JWT not in output


def test_mensagem_com_email_e_limpa():
    output = _log_through_pipeline(lambda logger: logger.warning("falha ao notificar %s", EMAIL))

    assert EMAIL not in output
    assert "[email]" in json.loads(output)["event"]
