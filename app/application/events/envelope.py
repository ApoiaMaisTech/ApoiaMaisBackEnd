from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# Contrato: contracts/events/envelope.v1.schema.json (o teste de contrato
# garante que este modelo e o JSON Schema dizem a mesma coisa).
PRODUCER = "apoiamais-api"


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID
    event_type: str = Field(pattern=r"^[a-z]+(\.[a-z]+)+$", max_length=100)
    version: int = Field(ge=1)
    occurred_at: datetime
    producer: str = Field(min_length=1, max_length=50)
    correlation_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    job_id: UUID | None = None
    payload: dict[str, Any]

    def to_json(self) -> str:
        return self.model_dump_json()


def new_event(
    event_type: str,
    version: int,
    payload: BaseModel,
    correlation_id: str,
    job_id: UUID | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        version=version,
        occurred_at=datetime.now(timezone.utc),
        producer=PRODUCER,
        correlation_id=correlation_id,
        job_id=job_id,
        payload=payload.model_dump(mode="json"),
    )
