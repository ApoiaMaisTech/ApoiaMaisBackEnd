from uuid import UUID, uuid4

from app.application.events.envelope import new_event
from app.application.events.evaluation import (
    EVALUATION_REQUESTED,
    EvaluationItemV1,
    EvaluationRequestedV1,
)
from app.domain.repositories.event_outbox import EventOutbox


class RequestEvaluationUseCase:
    """Pede a correção de uma atividade ao rust-evaluator (assíncrona, via RabbitMQ).

    O pedido vai para o outbox; o resultado volta como evaluation.completed ou
    evaluation.failed (app/infrastructure/messaging/handlers/evaluation_results.py).
    LGPD: o evento leva só gabarito e respostas, nunca quem é a criança; o vínculo
    evaluation_id -> criança fica na API.
    """

    def __init__(self, outbox: EventOutbox):
        self.outbox = outbox

    async def execute(
        self,
        items: list[EvaluationItemV1],
        correlation_id: str,
        evaluation_id: UUID | None = None,
    ) -> UUID:
        evaluation_id = evaluation_id or uuid4()
        payload = EvaluationRequestedV1(evaluation_id=evaluation_id, items=items)
        event = new_event(EVALUATION_REQUESTED, 1, payload, correlation_id=correlation_id, job_id=evaluation_id)
        await self.outbox.publish(event)
        return evaluation_id
