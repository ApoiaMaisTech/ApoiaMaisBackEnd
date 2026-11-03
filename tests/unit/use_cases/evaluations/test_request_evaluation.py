import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator

from app.application.events.evaluation import EVALUATION_REQUESTED, EvaluationItemV1
from app.application.use_cases.evaluations.request_evaluation_usecase import RequestEvaluationUseCase
from app.domain.repositories.event_outbox import EventOutbox

CONTRACTS = Path(__file__).resolve().parents[4] / "contracts" / "events"


class FakeOutbox(EventOutbox):
    def __init__(self):
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


def _schema(name):
    return Draft202012Validator(json.loads((CONTRACTS / name).read_text(encoding="utf-8")))


@pytest.mark.asyncio
async def test_pedido_vai_para_o_outbox_dentro_do_contrato():
    outbox = FakeOutbox()
    items = [
        EvaluationItemV1(item_id="p1", kind="text", answer=["casa"], expected=["casa"], max_typos=1),
        EvaluationItemV1(item_id="v1", kind="choice", answer=["a"], expected=["a", "e"]),
    ]

    evaluation_id = await RequestEvaluationUseCase(outbox).execute(items, correlation_id="req-123")

    [event] = outbox.events
    assert event.event_type == EVALUATION_REQUESTED and event.version == 1
    assert event.job_id == evaluation_id
    assert event.correlation_id == "req-123"
    body = json.loads(event.to_json())
    _schema("envelope.v1.schema.json").validate(body)
    _schema("evaluation.requested.v1.schema.json").validate(body["payload"])
    assert body["payload"]["evaluation_id"] == str(evaluation_id)


@pytest.mark.asyncio
async def test_payload_nao_tem_dado_da_crianca():
    outbox = FakeOutbox()
    items = [EvaluationItemV1(item_id="p1", kind="text", answer=["bola"], expected=["bola"])]

    await RequestEvaluationUseCase(outbox).execute(items, correlation_id="req-1", evaluation_id=uuid4())

    payload = outbox.events[0].payload
    assert set(payload) == {"evaluation_id", "items"}
    assert set(payload["items"][0]) <= {
        "item_id", "kind", "answer", "expected", "ignore_case", "ignore_accents", "max_typos", "tolerance",
    }
