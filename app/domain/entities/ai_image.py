from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.ai_image import AiImageStatus


@dataclass
class AiImage:
    id: UUID
    stage_id: UUID
    requested_by_user_id: UUID | None
    dedupe_key: str | None
    prompt: str
    prompt_hash: str
    status: AiImageStatus
    storage_key: str
    provider: str | None = None
    model: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    error_code: str | None = None
    correlation_id: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class StageTheme:
    stage_name: str
    world_name: str
