"""Contrato dos eventos: JSON Schema (contracts/events) == modelos Pydantic.

Os mesmos exemplos são lidos pelos testes do go-worker, então Python e Go
concordam sobre o formato sem compartilhar código.
"""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from app.application.events.ai_image import (
    AI_IMAGE_REQUESTED,
    AiImageFailedV1,
    AiImageGeneratedV1,
    AiImageRequestedV1,
    AiImageStartedV1,
    storage_key_for,
)
from app.application.events.envelope import EventEnvelope, new_event

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "events"
PAYLOADS = {
    ("ai.image.requested", 1): AiImageRequestedV1,
    ("ai.image.started", 1): AiImageStartedV1,
    ("ai.image.generated", 1): AiImageGeneratedV1,
    ("ai.image.failed", 1): AiImageFailedV1,
}
EXAMPLES = sorted((CONTRACTS / "examples").glob("*.json"))


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(event: dict) -> None:
    _validator("envelope.v1.schema.json").validate(event)
    _validator(f"{event['event_type']}.v{event['version']}.schema.json").validate(event["payload"])


def test_todo_payload_tem_schema_e_exemplo():
    example_names = {p.name for p in EXAMPLES}
    for event_type, version in PAYLOADS:
        assert (CONTRACTS / f"{event_type}.v{version}.schema.json").exists()
        assert f"{event_type}.v{version}.json" in example_names


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_exemplos_validam_no_schema_e_no_pydantic(path):
    event = json.loads(path.read_text(encoding="utf-8"))

    _validate(event)
    envelope = EventEnvelope.model_validate(event)
    PAYLOADS[(envelope.event_type, envelope.version)].model_validate(envelope.payload)


def test_evento_gerado_pela_api_respeita_o_schema():
    image_id = uuid4()
    envelope = new_event(
        AI_IMAGE_REQUESTED,
        1,
        AiImageRequestedV1(image_id=image_id, prompt="Tema: vogais", storage_key=storage_key_for(image_id)),
        correlation_id="abc-123",
        job_id=image_id,
    )

    _validate(json.loads(envelope.to_json()))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("event_id"),
        lambda e: e.update(extra="campo"),
        lambda e: e.update(version=0),
        lambda e: e.update(event_type="AI.Image"),
        lambda e: e.update(correlation_id="tem espaço"),
    ],
    ids=["sem-event-id", "campo-extra", "versao-zero", "tipo-invalido", "correlation-invalido"],
)
def test_envelope_invalido_e_rejeitado_pelos_dois_lados(mutate):
    event = json.loads((CONTRACTS / "examples" / "ai.image.generated.v1.json").read_text())
    mutate(event)

    with pytest.raises(Exception):
        _validator("envelope.v1.schema.json").validate(event)
    with pytest.raises(Exception):
        EventEnvelope.model_validate(event)


@pytest.mark.parametrize(
    "storage_key",
    ["../etc/passwd", "ai-images/../../x.png", "outro/abc.png", "ai-images/ABC.png"],
)
def test_storage_key_fora_do_padrao_e_rejeitada(storage_key):
    payload = {"image_id": str(uuid4()), "prompt": "x", "size": "1024x1024", "storage_key": storage_key}

    with pytest.raises(Exception):
        _validator("ai.image.requested.v1.schema.json").validate(payload)
    with pytest.raises(Exception):
        AiImageRequestedV1.model_validate(payload)
