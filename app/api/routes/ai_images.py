from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies.ai_images import (
    get_ai_image_content_usecase,
    get_ai_image_usecase,
    get_request_stage_illustration_usecase,
)
from app.api.dependencies.auth import get_current_user, require_roles
from app.api.dependencies.rate_limit import rate_limit
from app.application.dto.ai_image_response import AiImageResponse
from app.application.use_cases.ai_images.get_ai_image_usecase import (
    GetAiImageContentUseCase,
    GetAiImageUseCase,
)
from app.application.use_cases.ai_images.request_stage_illustration_usecase import (
    RequestStageIllustrationUseCase,
)
from app.core.config import settings
from app.core.logging import get_correlation_id
from app.domain.enums.ai_image import AiImageStatus
from app.domain.enums.user import UserRole

router = APIRouter()

# Matriz de autorização (testada em tests/integration/api/test_ai_images_routes.py):
#   rota                                   anônimo  aluno  professor
#   POST /stages/{id}/illustration         401      ok     ok
#   GET  /ai-images/{id}                   401      ok     ok
#   GET  /ai-images/{id}/content           401      ok     ok
# As ilustrações são da fase (conteúdo do jogo), não da criança.

can_request = require_roles(UserRole.STUDENT, UserRole.TEACHER)


@router.post(
    "/stages/{stage_id}/illustration",
    response_model=AiImageResponse,
    responses={202: {"model": AiImageResponse}},
    dependencies=[Depends(rate_limit("ai-image", settings.RATE_LIMIT_AI_IMAGE))],
)
async def request_stage_illustration(
    stage_id: UUID,
    response: Response,
    current_user: dict = Depends(can_request),
    use_case: RequestStageIllustrationUseCase = Depends(get_request_stage_illustration_usecase),
):
    image = await use_case.execute(stage_id, current_user["id"], get_correlation_id())
    if image.status in (AiImageStatus.PENDING, AiImageStatus.PROCESSING):
        response.status_code = status.HTTP_202_ACCEPTED
    return AiImageResponse.from_entity(image)


@router.get("/ai-images/{image_id}", response_model=AiImageResponse)
async def get_ai_image(
    image_id: UUID,
    current_user: dict = Depends(get_current_user),
    use_case: GetAiImageUseCase = Depends(get_ai_image_usecase),
):
    return AiImageResponse.from_entity(await use_case.execute(image_id))


@router.get(
    "/ai-images/{image_id}/content",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
async def get_ai_image_content(
    image_id: UUID,
    current_user: dict = Depends(get_current_user),
    use_case: GetAiImageContentUseCase = Depends(get_ai_image_content_usecase),
):
    content, mime_type = await use_case.execute(image_id)
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
