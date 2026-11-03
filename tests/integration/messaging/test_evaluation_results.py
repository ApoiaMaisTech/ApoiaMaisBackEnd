"""Resultados do rust-evaluator no api-worker (MySQL real para o inbox)."""
import json
import logging
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.application.events.envelope import EventEnvelope
from app.infrastructure.database.models.messaging.outbox_event_model import OutboxEventModel
from app.infrastructure.database.models.messaging.processed_event_model import ProcessedEventModel
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.messaging.consumer import PermanentError
from app.infrastructure.messaging.handlers.evaluation_results import CONSUMER_NAME, EvaluationResultHandlers
from app.infrastructure.messaging.outbox import SqlEventOutbox

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "events" / "examples"

pytestmark = pytest.mark.asyncio


def _example(name: str, **changes) -> EventEnvelope:
    data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    data["event_id"] = str(uuid4())
    for key, value in changes.items():
        data["payload"][key] = value
    return EventEnvelope.model_validate(data)


async def _markers(event_id) -> int:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(ProcessedEventModel).where(
                ProcessedEventModel.consumer == CONSUMER_NAME,
                ProcessedEventModel.event_id == str(event_id),
            )
        )
        return len(rows.scalars().all())


async def test_resultado_e_processado_uma_vez(caplog):
    handlers = EvaluationResultHandlers(AsyncSessionLocal)
    event = _example("evaluation.completed.v1.json")

    with caplog.at_level(logging.INFO, logger="apoiamais.evaluation_results"):
        await handlers.on_completed(event)
        await handlers.on_completed(event)  # reentrega

    assert await _markers(event.event_id) == 1
    logged = [r for r in caplog.records if r.getMessage() == "avaliação concluída"]
    assert len(logged) == 1
    assert logged[0].score == 0.7292
    # nunca as respostas da criança no log
    assert "Caza" not in caplog.text and "avo" not in caplog.text


async def test_falha_e_registrada_uma_vez():
    handlers = EvaluationResultHandlers(AsyncSessionLocal)
    event = _example("evaluation.failed.v1.json")

    await handlers.on_failed(event)
    await handlers.on_failed(event)

    assert await _markers(event.event_id) == 1


@pytest.mark.parametrize(
    "changes",
    [{"score": 1.5}, {"correct_items": 9}, {"engine": ""}, {"extra": True}],
    ids=["score-fora", "totais-inconsistentes", "engine-vazio", "campo-desconhecido"],
)
async def test_resultado_fora_do_contrato_e_erro_permanente(changes):
    handlers = EvaluationResultHandlers(AsyncSessionLocal)
    event = _example("evaluation.completed.v1.json", **changes)

    with pytest.raises(PermanentError):
        await handlers.on_completed(event)
    assert await _markers(event.event_id) == 0


async def test_job_id_diferente_e_recusado():
    handlers = EvaluationResultHandlers(AsyncSessionLocal)
    data = json.loads((EXAMPLES / "evaluation.completed.v1.json").read_text(encoding="utf-8"))
    data["event_id"], data["job_id"] = str(uuid4()), str(uuid4())

    with pytest.raises(PermanentError):
        await handlers.on_completed(EventEnvelope.model_validate(data))


async def test_outbox_sql_grava_o_pedido(clean_outbox):
    from app.application.events.evaluation import EvaluationItemV1
    from app.application.use_cases.evaluations.request_evaluation_usecase import RequestEvaluationUseCase

    items = [EvaluationItemV1(item_id="p1", kind="text", answer=["casa"], expected=["casa"])]
    async with AsyncSessionLocal() as session:
        evaluation_id = await RequestEvaluationUseCase(SqlEventOutbox(session)).execute(items, "req-outbox")

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(OutboxEventModel))).scalars().all()
    [row] = [r for r in rows if r.event_type == "evaluation.requested"]
    assert row.routing_key == "evaluation.requested"
    assert row.published_at is None
    assert json.loads(row.body)["payload"]["evaluation_id"] == str(evaluation_id)
