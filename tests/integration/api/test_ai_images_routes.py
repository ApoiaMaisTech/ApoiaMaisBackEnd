from uuid import uuid4

import pytest

from main import app

from app.api.dependencies.ai_images import get_storage
from app.api.dependencies.repositories import get_ai_image_repository
from app.domain.entities.ai_image import StageTheme
from app.domain.enums.ai_image import AiImageStatus
from app.domain.enums.user import UserRole

from tests.fakes.ai_images import InMemoryAiImageRepository, InMemoryStorage
from tests.integration.api.helpers import auth_header

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def images():
    repository = InMemoryAiImageRepository()
    app.dependency_overrides[get_ai_image_repository] = lambda: repository
    return repository


@pytest.fixture
def storage():
    fake = InMemoryStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    return fake


@pytest.fixture
def stage_id(images):
    sid = uuid4()
    images.stages[sid] = StageTheme(stage_name="Vogais", world_name="Floresta")
    return sid


def _request(client, stage_id, headers=None):
    return client.post(f"/api/stages/{stage_id}/illustration", headers=headers or {})


def test_sem_token_retorna_401(client, images, stage_id):
    assert _request(client, stage_id).status_code == 401
    assert client.get(f"/api/ai-images/{uuid4()}").status_code == 401
    assert client.get(f"/api/ai-images/{uuid4()}/content").status_code == 401


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.TEACHER])
def test_aluno_e_professor_pedem_ilustracao(client, make_user, images, stage_id, role):
    response = _request(client, stage_id, auth_header(make_user(role)))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["image_url"] is None
    assert body["retry_after_seconds"] > 0
    # nada interno na resposta
    assert set(body) == {"id", "status", "image_url", "retry_after_seconds"}


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.DOCTOR])
def test_outros_perfis_nao_pedem_ilustracao(client, make_user, images, stage_id, role):
    assert _request(client, stage_id, auth_header(make_user(role))).status_code == 403


def test_fase_inexistente_retorna_404(client, make_user, images):
    response = _request(client, uuid4(), auth_header(make_user(UserRole.STUDENT)))

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_fluxo_completo_polling_e_conteudo(client, make_user, images, storage, stage_id):
    headers = auth_header(make_user(UserRole.STUDENT))
    image_id = _request(client, stage_id, headers).json()["id"]

    # ainda não pronta
    assert client.get(f"/api/ai-images/{image_id}", headers=headers).json()["status"] == "pending"
    assert client.get(f"/api/ai-images/{image_id}/content", headers=headers).status_code == 409

    # o worker terminou
    image = next(iter(images.images.values()))
    storage.objects[image.storage_key] = PNG
    images.set_status(image.id, AiImageStatus.COMPLETED, mime_type="image/png")

    status = client.get(f"/api/ai-images/{image_id}", headers=headers).json()
    assert status["status"] == "completed"
    assert status["image_url"] == f"/api/ai-images/{image_id}/content"

    content = client.get(status["image_url"], headers=headers)
    assert content.status_code == 200
    assert content.content == PNG
    assert content.headers["content-type"] == "image/png"
    assert content.headers["x-content-type-options"] == "nosniff"

    # a próxima criança na mesma fase recebe a imagem pronta direto (200)
    other = _request(client, stage_id, auth_header(make_user(UserRole.STUDENT)))
    assert other.status_code == 200
    assert other.json()["id"] == image_id


def test_imagem_inexistente_retorna_404(client, make_user, images, storage):
    headers = auth_header(make_user(UserRole.STUDENT))

    assert client.get(f"/api/ai-images/{uuid4()}", headers=headers).status_code == 404
    assert client.get(f"/api/ai-images/{uuid4()}/content", headers=headers).status_code == 404


def test_cota_diaria_retorna_429(client, make_user, images, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AI_IMAGE_DAILY_QUOTA_PER_USER", 1)
    headers = auth_header(make_user(UserRole.STUDENT))
    stages = [uuid4(), uuid4()]
    for i, sid in enumerate(stages):
        images.stages[sid] = StageTheme(stage_name=f"Fase {i}", world_name="Mundo")

    assert _request(client, stages[0], headers).status_code == 202
    response = _request(client, stages[1], headers)

    assert response.status_code == 429
    assert response.json()["success"] is False
