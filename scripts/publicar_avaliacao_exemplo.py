"""Publica uma avaliação de exemplo para o rust-evaluator (via outbox, como a API faz).

Uso:
    python -m scripts.publicar_avaliacao_exemplo
    docker compose run --rm api-worker python -m scripts.publicar_avaliacao_exemplo

O pedido é gravado no outbox (MySQL); o api-worker publica no RabbitMQ, o
rust-evaluator corrige e o api-worker registra o resultado no log
("avaliação concluída", com o mesmo evaluation_id e correlation_id):

    docker compose logs -f api-worker rust-evaluator

Os itens vêm de contracts/events/examples/evaluation.requested.v1.json.
"""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.application.events.evaluation import EvaluationItemV1
from app.application.use_cases.evaluations.request_evaluation_usecase import RequestEvaluationUseCase
from app.infrastructure.database.session import AsyncSessionLocal, engine
from app.infrastructure.messaging.outbox import SqlEventOutbox

EXAMPLE = Path(__file__).resolve().parent.parent / "contracts" / "events" / "examples" / "evaluation.requested.v1.json"


async def main() -> None:
    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    items = [EvaluationItemV1.model_validate(item) for item in example["payload"]["items"]]
    correlation_id = f"exemplo-{uuid4().hex[:12]}"

    async with AsyncSessionLocal() as session:
        evaluation_id = await RequestEvaluationUseCase(SqlEventOutbox(session)).execute(items, correlation_id)
    await engine.dispose()

    print(json.dumps({"evaluation_id": str(evaluation_id), "correlation_id": correlation_id, "items": len(items)}))


if __name__ == "__main__":
    asyncio.run(main())
