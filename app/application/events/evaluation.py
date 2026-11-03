"""Payloads dos eventos de avaliação de atividades (versão 1).

Contratos: contracts/events/evaluation.*.v1.schema.json. A API publica
evaluation.requested; o rust-evaluator (workers/rust-evaluator) corrige e
devolve evaluation.completed ou evaluation.failed.

LGPD: o pedido leva só gabarito e respostas. Nada que identifique a criança
(nome, paciente, diagnóstico) entra no evento; a API guarda o vínculo
evaluation_id -> criança do lado dela.
"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EVALUATION_REQUESTED = "evaluation.requested"
EVALUATION_COMPLETED = "evaluation.completed"
EVALUATION_FAILED = "evaluation.failed"

ITEM_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationItemV1(_Payload):
    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    kind: Literal["text", "choice", "number"]
    # text e number: exatamente 1 elemento; choice: opções marcadas (pode ser vazio)
    answer: list[str] = Field(max_length=50)
    # text e number: respostas aceitas; choice: conjunto de opções corretas
    expected: list[str] = Field(min_length=1, max_length=50)
    ignore_case: bool = True
    ignore_accents: bool = False
    max_typos: int = Field(default=0, ge=0, le=3)
    tolerance: float = Field(default=0, ge=0)


class EvaluationRequestedV1(_Payload):
    evaluation_id: UUID
    items: list[EvaluationItemV1] = Field(min_length=1, max_length=200)


class EvaluationItemResultV1(_Payload):
    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    correct: bool
    score: float = Field(ge=0, le=1)


class EvaluationCompletedV1(_Payload):
    evaluation_id: UUID
    total_items: int = Field(ge=1, le=200)
    correct_items: int = Field(ge=0, le=200)
    score: float = Field(ge=0, le=1)
    items: list[EvaluationItemResultV1] = Field(min_length=1, max_length=200)
    engine: str = Field(min_length=1, max_length=50)
    engine_version: str = Field(min_length=1, max_length=50)


class EvaluationFailedV1(_Payload):
    evaluation_id: UUID
    error_code: str = Field(pattern=r"^[a-z_]{1,50}$")
    error_message: str = Field(default="", max_length=500)
    retryable: bool = False
