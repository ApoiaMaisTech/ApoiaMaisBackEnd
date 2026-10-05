"""Payloads dos eventos de ilustração por IA (versão 1).

Contratos: contracts/events/ai.image.*.v1.schema.json. Mudança aditiva e
opcional mantém a versão; qualquer outra mudança cria a v2 e os consumidores
aceitam as duas durante a transição.
"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AI_IMAGE_REQUESTED = "ai.image.requested"
AI_IMAGE_STARTED = "ai.image.started"
AI_IMAGE_GENERATED = "ai.image.generated"
AI_IMAGE_FAILED = "ai.image.failed"

# chave fixa e previsível: o worker só pode gravar aqui, e a API confere ao receber
STORAGE_KEY_PATTERN = r"^ai-images/[0-9a-f]{32}\.png$"
ALLOWED_MIME_TYPES = ("image/png",)


def storage_key_for(image_id: UUID) -> str:
    return f"ai-images/{image_id.hex}.png"


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AiImageRequestedV1(_Payload):
    image_id: UUID
    # montado no servidor a partir de template + tema da fase; nunca dados da criança
    prompt: str = Field(min_length=1, max_length=1000)
    size: Literal["1024x1024"] = "1024x1024"
    storage_key: str = Field(pattern=STORAGE_KEY_PATTERN)


class AiImageStartedV1(_Payload):
    image_id: UUID


class AiImageGeneratedV1(_Payload):
    image_id: UUID
    storage_key: str = Field(pattern=STORAGE_KEY_PATTERN)
    mime_type: Literal["image/png"]
    size_bytes: int = Field(gt=0, le=20 * 1024 * 1024)
    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=100)


class AiImageFailedV1(_Payload):
    image_id: UUID
    error_code: str = Field(pattern=r"^[a-z_]{1,50}$")
    error_message: str = Field(default="", max_length=500)
    retryable: bool = False
