"""Resultados do rust-evaluator (evaluation.completed / evaluation.failed v1).

Cada evento é processado uma única vez (inbox processed_event). Ainda não há
tabela de avaliações: o resultado é registrado em log estruturado (ids e notas,
nunca as respostas). Quando a atividade existir no banco, `on_completed` /
`on_failed` passam a gravar o resultado dentro do mesmo `apply` (mesma transação
da marca de processado), sem mudar o resto do fluxo.
"""
import logging

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.events.envelope import EventEnvelope
from app.application.events.evaluation import (
    EVALUATION_COMPLETED,
    EVALUATION_FAILED,
    EvaluationCompletedV1,
    EvaluationFailedV1,
)
from app.infrastructure.messaging.consumer import Handler, PermanentError
from app.infrastructure.messaging.inbox import process_once

logger = logging.getLogger("apoiamais.evaluation_results")

CONSUMER_NAME = "apoiamais-api.evaluation-results"
QUEUE_NAME = "apoiamais-api.evaluation-results"


def _parse(model, envelope: EventEnvelope):
    try:
        payload = model.model_validate(envelope.payload)
    except ValidationError as exc:
        raise PermanentError(f"payload inválido para {envelope.event_type}") from exc
    if envelope.job_id is not None and envelope.job_id != payload.evaluation_id:
        raise PermanentError("job_id diferente de evaluation_id")
    return payload


class EvaluationResultHandlers:
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    def handlers(self) -> dict[tuple[str, int], Handler]:
        return {
            (EVALUATION_COMPLETED, 1): self.on_completed,
            (EVALUATION_FAILED, 1): self.on_failed,
        }

    async def on_completed(self, envelope: EventEnvelope) -> None:
        payload = _parse(EvaluationCompletedV1, envelope)
        if payload.correct_items > payload.total_items or len(payload.items) != payload.total_items:
            raise PermanentError("totais inconsistentes no resultado")

        async def apply(session: AsyncSession) -> None:
            logger.info(
                "avaliação concluída",
                extra={
                    "evaluation_id": str(payload.evaluation_id),
                    "score": payload.score,
                    "correct_items": payload.correct_items,
                    "total_items": payload.total_items,
                    "engine_version": payload.engine_version,
                },
            )

        await process_once(self._session_factory, CONSUMER_NAME, envelope, apply)

    async def on_failed(self, envelope: EventEnvelope) -> None:
        payload = _parse(EvaluationFailedV1, envelope)

        async def apply(session: AsyncSession) -> None:
            logger.warning(
                "avaliação recusada pelo rust-evaluator",
                extra={
                    "evaluation_id": str(payload.evaluation_id),
                    "error_code": payload.error_code,
                    "retryable": payload.retryable,
                },
            )

        await process_once(self._session_factory, CONSUMER_NAME, envelope, apply)
