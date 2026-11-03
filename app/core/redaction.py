"""Remoção de dados pessoais e segredos antes de logar ou persistir texto de erro (LGPD).

Duas camadas:
- por chave: qualquer campo cujo nome indique dado sensível vira "[redacted]"
  (password, token, authorization, email, cpf, telefone, nascimento, clínico...);
- por conteúdo: em textos livres (mensagem, traceback, erro de biblioteca) e-mails,
  JWTs, tokens Bearer, CPFs, hashes de senha e os parâmetros de SQL do SQLAlchemy
  ("[parameters: ...]") são substituídos por marcadores.

Usado no pipeline de logs (app/core/logging.py) e onde texto de exceção é gravado
fora do processo (header x-last-error no RabbitMQ, outbox_event.last_error).
"""
import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[redacted]"

# trechos de nome de campo que indicam dado sensível (comparação sem caixa)
SENSITIVE_KEY_PARTS = (
    "password",
    "senha",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "private_key",
    "email",
    "cpf",
    "rg_",
    "phone",
    "telefone",
    "birth",
    "nascimento",
    "clinical",
    "clinico",
    "diagnos",
    "prontuario",
)

# campos estruturais do próprio log que nunca são sensíveis
_SAFE_KEYS = frozenset({"event", "level", "logger", "timestamp", "correlation_id", "event_id", "event_type"})

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # parâmetros que o SQLAlchemy anexa à mensagem de erro (podem ter email, hash, nome...)
    (re.compile(r"\[parameters: .*?\](?=\s*(?:\n|\(Background|$))", re.DOTALL), "[parameters: [redacted]]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [redacted]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[jwt]"),
    (re.compile(r"\b(?:pbkdf2|argon2|bcrypt|scrypt)[^\s'\",)]*\$[^\s'\",)]+"), "[hash]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[cpf]"),
)


def is_sensitive_key(key: str) -> bool:
    if key in _SAFE_KEYS:
        return False
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact_text(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(value: Any, _depth: int = 0) -> Any:
    """Copia `value` trocando dados sensíveis. Não altera o objeto original."""
    if _depth > 8:
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            k: (REDACTED if isinstance(k, str) and is_sensitive_key(k) else redact(v, _depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return type(value)(redact(v, _depth + 1) for v in value)
    return value


def redact_processor(_logger, _method_name: str, event_dict: dict) -> dict:
    """Processor do structlog: roda depois de format_exc_info, então limpa o traceback também."""
    return redact(event_dict)


def safe_error_text(exc: BaseException, limit: int = 300) -> str:
    """Texto curto de uma exceção, sem dados pessoais, para gravar fora do processo."""
    return redact_text(f"{type(exc).__name__}: {exc}")[:limit]
