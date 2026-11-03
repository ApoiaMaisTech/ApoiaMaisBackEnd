"""Normalização de entrada compartilhada pelos DTOs de requisição.

Senha nunca é normalizada (espaços fazem parte dela); nome e email sim.
"""
import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, EmailStr, Field

_SPACES = re.compile(r"\s+")


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _normalize_name(value: str) -> str:
    # "  Ana   Maria " -> "Ana Maria"; caracteres de controle não são aceitos
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("o nome contém caracteres inválidos")
    return _SPACES.sub(" ", value)


# email sem espaços nas pontas e em minúsculas: evita contas duplicadas por caixa
Email = Annotated[EmailStr, BeforeValidator(_strip), AfterValidator(lambda v: v.lower())]

PersonName = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=3, max_length=100),
    AfterValidator(_normalize_name),
]

# 8..128: o limite superior evita hash PBKDF2 de payloads enormes
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]
