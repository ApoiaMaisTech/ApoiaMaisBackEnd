from functools import lru_cache

from fastapi import Depends

from app.api.dependencies.repositories import get_ai_image_repository
from app.application.use_cases.ai_images.get_ai_image_usecase import (
    GetAiImageContentUseCase,
    GetAiImageUseCase,
)
from app.application.use_cases.ai_images.request_stage_illustration_usecase import (
    RequestStageIllustrationUseCase,
)
from app.core.config import settings
from app.infrastructure.storage import ObjectStorage, build_storage


@lru_cache
def get_storage() -> ObjectStorage:
    return build_storage(settings)


def get_request_stage_illustration_usecase(
    repository=Depends(get_ai_image_repository),
) -> RequestStageIllustrationUseCase:
    return RequestStageIllustrationUseCase(
        repository=repository,
        daily_quota_per_user=settings.AI_IMAGE_DAILY_QUOTA_PER_USER,
        failure_cooldown_minutes=settings.AI_IMAGE_FAILURE_COOLDOWN_MINUTES,
    )


def get_ai_image_usecase(repository=Depends(get_ai_image_repository)) -> GetAiImageUseCase:
    return GetAiImageUseCase(repository=repository)


def get_ai_image_content_usecase(
    repository=Depends(get_ai_image_repository),
    storage: ObjectStorage = Depends(get_storage),
) -> GetAiImageContentUseCase:
    return GetAiImageContentUseCase(repository=repository, storage=storage)
