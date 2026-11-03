"""Matriz de autorização: cada rota protegida x cada perfil (aluno, professor, admin, médico).

Exercita rotas, dependências e use cases reais (repositórios em memória). As
tabelas de referência estão no topo de app/api/routes/users.py e
app/api/routes/ai_images.py. Ao criar uma rota nova em /api, adicione as linhas
dela aqui: `test_matriz_cobre_todas_as_rotas_da_api` falha se faltar.

Política atual (negar por padrão): admin e médico ainda não têm regras de negócio
próprias, então só acessam a própria conta e as ilustrações do jogo.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest

from main import app

from app.api.dependencies.ai_images import get_storage
from app.api.dependencies.repositories import get_ai_image_repository
from app.core.config import settings
from app.domain.entities.ai_image import StageTheme
from app.domain.enums.ai_image import AiImageStatus
from app.domain.enums.user import UserRole

from tests.fakes.ai_images import InMemoryAiImageRepository, InMemoryStorage
from tests.integration.api.helpers import auth_header, forge_token

ANON, STUDENT, TEACHER, ADMIN, DOCTOR = "anonimo", "aluno", "professor", "admin", "medico"
ACTORS = (ANON, STUDENT, TEACHER, ADMIN, DOCTOR)
ROLE_OF = {STUDENT: UserRole.STUDENT, TEACHER: UserRole.TEACHER, ADMIN: UserRole.ADMIN, DOCTOR: UserRole.DOCTOR}

# alvos das rotas /{id}: o próprio ator ou uma conta de outro perfil
SELF = "self"
OTHER = {STUDENT: "outro_aluno", TEACHER: "outro_professor", ADMIN: "outro_admin", DOCTOR: "outro_medico"}
TARGETS = (SELF, *OTHER.values())

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _all(status: int) -> dict:
    return {target: status for target in TARGETS}


def _only_self(ok: int) -> dict:
    return {target: (ok if target == SELF else 403) for target in TARGETS}


# Política por rota. Rotas sem alvo: ator -> status. Rotas com {id}: ator -> {alvo -> status}.
POLICY: dict[tuple[str, str], dict] = {
    ("POST", "/api/users/students"): {ANON: 401, STUDENT: 403, TEACHER: 201, ADMIN: 403, DOCTOR: 403},
    ("POST", "/api/users/teachers"): {ANON: 401, STUDENT: 403, TEACHER: 201, ADMIN: 403, DOCTOR: 403},
    ("GET", "/api/users/"): {ANON: 401, STUDENT: 403, TEACHER: 200, ADMIN: 403, DOCTOR: 403},
    ("GET", "/api/users/{id}"): {
        ANON: _all(401),
        STUDENT: _only_self(200),
        TEACHER: _all(200),
        ADMIN: _only_self(200),
        DOCTOR: _only_self(200),
    },
    ("PUT", "/api/users/{id}"): {
        ANON: _all(401),
        STUDENT: _only_self(200),
        TEACHER: _only_self(200),
        ADMIN: _only_self(200),
        DOCTOR: _only_self(200),
    },
    ("DELETE", "/api/users/{id}"): {
        ANON: _all(401),
        STUDENT: _all(403),
        # professor remove só contas de aluno (nem a própria conta)
        TEACHER: {t: (204 if t == OTHER[STUDENT] else 403) for t in TARGETS},
        ADMIN: _all(403),
        DOCTOR: _all(403),
    },
    ("POST", "/api/stages/{stage_id}/illustration"): {ANON: 401, STUDENT: 202, TEACHER: 202, ADMIN: 403, DOCTOR: 403},
    # ilustrações são conteúdo da fase (não da criança): qualquer perfil autenticado vê
    ("GET", "/api/ai-images/{image_id}"): {ANON: 401, STUDENT: 200, TEACHER: 200, ADMIN: 200, DOCTOR: 200},
    ("GET", "/api/ai-images/{image_id}/content"): {ANON: 401, STUDENT: 200, TEACHER: 200, ADMIN: 200, DOCTOR: 200},
}

# rotas públicas de propósito (fora da matriz)
PUBLIC = {("POST", "/api/auth/login")}


def _rows():
    for (method, path), by_actor in POLICY.items():
        for actor in ACTORS:
            expected = by_actor[actor]
            if isinstance(expected, dict):
                for target, status in expected.items():
                    yield method, path, target, actor, status
            else:
                yield method, path, None, actor, expected


MATRIX = list(_rows())


def _new_user_body():
    return {"name": "Novo Usuário", "email": f"{uuid4().hex[:8]}@example.com", "password": "senha-nova-123"}


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
def world(make_user, images, storage):
    """Um usuário de cada perfil (ator e "outro"), uma fase nova e uma fase com imagem."""
    users = {actor: make_user(role) for actor, role in ROLE_OF.items()}
    users.update({OTHER[actor]: make_user(role) for actor, role in ROLE_OF.items()})

    stage_id = uuid4()
    images.stages[stage_id] = StageTheme(stage_name="Vogais", world_name="Floresta")

    ready_stage = uuid4()
    images.stages[ready_stage] = StageTheme(stage_name="Consoantes", world_name="Rio")

    return {"users": users, "stage_id": stage_id, "ready_stage": ready_stage}


def _completed_image(client, images, storage, stage_id, owner):
    response = client.post(f"/api/stages/{stage_id}/illustration", headers=auth_header(owner))
    assert response.status_code == 202, response.text
    image = images.images[UUID(response.json()["id"])]
    storage.objects[image.storage_key] = PNG
    images.set_status(image.id, AiImageStatus.COMPLETED, mime_type="image/png")
    return image


@pytest.mark.parametrize(
    "method,path,target,actor,expected",
    MATRIX,
    ids=[f"{m} {p} alvo={t} ator={a} -> {e}" for m, p, t, a, e in MATRIX],
)
def test_matriz_de_autorizacao(client, repo, images, storage, world, method, path, target, actor, expected):
    users = world["users"]
    headers = auth_header(users[actor]) if actor != ANON else {}

    target_user = None
    if target == SELF:
        target_user = users[actor] if actor != ANON else users[STUDENT]
    elif target is not None:
        target_user = users[target]

    url = path
    if "{id}" in path:
        url = path.replace("{id}", str(target_user.id))
    if "{stage_id}" in path:
        url = path.replace("{stage_id}", str(world["stage_id"]))
    if "{image_id}" in path:
        image = _completed_image(client, images, storage, world["ready_stage"], users[TEACHER])
        url = path.replace("{image_id}", str(image.id))

    body = None
    if method == "POST" and path.startswith("/api/users"):
        body = _new_user_body()
    elif method == "PUT":
        body = {"email": target_user.email, "password": "senha-alterada-123"}

    total_users = len(repo.users)
    total_images = len(images.images)
    snapshot = {uid: (u.email, u.password_hash, u.role) for uid, u in repo.users.items()}

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == expected, response.text

    # negado não pode ter efeito colateral
    if expected in (401, 403):
        assert len(repo.users) == total_users
        assert len(images.images) == total_images
        assert {uid: (u.email, u.password_hash, u.role) for uid, u in repo.users.items()} == snapshot
        body = response.json()
        assert body["success"] is False
        assert body["code"] in ("UNAUTHORIZED", "FORBIDDEN")
        assert body["message"]
    if expected == 401:
        assert response.headers.get("www-authenticate") == "Bearer"


def test_matriz_cobre_todas_as_rotas_da_api():
    existentes = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api")
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
    }
    existentes = {(m, p.replace("{user_id}", "{id}")) for m, p in existentes}
    faltando = existentes - set(POLICY) - PUBLIC
    assert faltando == set(), f"rota sem linha na matriz de autorização: {faltando}"
    # e nenhuma linha antiga sobrando para rota que não existe mais
    assert set(POLICY) - existentes == set()


def test_matriz_tem_todos_os_perfis():
    assert set(ROLE_OF.values()) == set(UserRole), "perfil novo precisa entrar na matriz"
    for by_actor in POLICY.values():
        assert set(by_actor) == set(ACTORS)


# --- tokens ------------------------------------------------------------------

@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({"Authorization": "Bearer nao-e-um-jwt"}, id="token-malformado"),
        pytest.param({"Authorization": "Basic dXNlcjpwYXNz"}, id="esquema-errado"),
        pytest.param({"Authorization": "Bearer "}, id="bearer-vazio"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "teacher"}, secret="outro-segredo"), id="assinatura-invalida"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "teacher", "exp": 1}), id="expirado"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "superuser"}), id="role-desconhecida"),
        pytest.param(forge_token({"user_id": "nao-e-uuid", "role": "teacher"}), id="user-id-invalido"),
        pytest.param(forge_token({"role": "teacher"}), id="sem-user-id"),
        pytest.param(forge_token({"user_id": str(uuid4())}), id="sem-role"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "teacher"}), id="usuario-inexistente"),
    ],
)
def test_tokens_invalidos_retornam_401(client, repo, headers):
    response = client.get("/api/users/", headers=headers)

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_token_sem_expiracao_e_recusado(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    token = jwt.encode(
        {"user_id": str(teacher.id), "role": "teacher"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    response = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_token_com_alg_none_e_recusado(client, make_user):
    teacher = make_user(UserRole.TEACHER)
    payload = {
        "user_id": str(teacher.id),
        "role": "teacher",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, key=None, algorithm="none")

    response = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_token_de_usuario_removido_perde_acesso_na_hora(client, make_user, repo):
    teacher = make_user(UserRole.TEACHER)
    headers = auth_header(teacher)
    assert client.get("/api/users/", headers=headers).status_code == 200

    repo.users.pop(teacher.id)

    response = client.get("/api/users/", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"


def test_perfil_vale_o_do_banco_e_nao_o_do_token(client, make_user, repo):
    # token emitido quando a conta era de professor; depois foi rebaixada para aluno
    user = make_user(UserRole.TEACHER)
    stale_headers = auth_header(user)
    repo.users[user.id].role = UserRole.STUDENT

    assert client.get("/api/users/", headers=stale_headers).status_code == 403
    assert client.post("/api/users/teachers", json=_new_user_body(), headers=stale_headers).status_code == 403


def test_token_assinado_com_role_falsa_nao_eleva_privilegio(client, make_user):
    # mesmo que alguém consiga um token assinado dizendo "teacher", vale o perfil do banco
    student = make_user(UserRole.STUDENT)
    headers = forge_token({"user_id": str(student.id), "user_email": student.email, "role": "teacher"})

    assert client.get("/api/users/", headers=headers).status_code == 403


# --- escalada de privilégio pelo corpo da requisição -------------------------

def test_role_no_corpo_da_criacao_e_ignorada(client, make_user, repo):
    teacher = make_user(UserRole.TEACHER)
    body = {**_new_user_body(), "role": "teacher"}

    response = client.post("/api/users/students", json=body, headers=auth_header(teacher))

    assert response.status_code == 201
    assert response.json()["role"] == "student"
    created = next(u for u in repo.users.values() if u.email == body["email"])
    assert created.role == UserRole.STUDENT


@pytest.mark.parametrize(
    "extra",
    [{"role": "teacher"}, {"role": "administrador"}, {"id": str(uuid4())}, {"name": "Outro Nome"}],
    ids=["role-professor", "role-admin", "id", "nome"],
)
def test_atualizacao_nao_altera_role_id_ou_nome(client, make_user, repo, extra):
    student = make_user(UserRole.STUDENT)
    original = (student.id, student.name, student.role)

    response = client.put(
        f"/api/users/{student.id}",
        json={"email": student.email, "password": "senha-alterada-123", **extra},
        headers=auth_header(student),
    )

    assert response.status_code == 200
    stored = repo.users[student.id]
    assert (stored.id, stored.name, stored.role) == original
    assert response.json()["role"] == "student"


def test_aluno_nao_toma_o_email_de_outra_conta(client, make_user, repo):
    student = make_user(UserRole.STUDENT)
    teacher = make_user(UserRole.TEACHER)

    response = client.put(
        f"/api/users/{student.id}",
        json={"email": teacher.email, "password": "senha-alterada-123"},
        headers=auth_header(student),
    )

    assert response.status_code == 409
    assert repo.users[student.id].email == student.email


def test_uuid_em_maiusculas_nao_burla_a_checagem_de_dono(client, make_user):
    student = make_user(UserRole.STUDENT)
    other = make_user(UserRole.STUDENT)
    headers = auth_header(student)

    assert client.get(f"/api/users/{str(other.id).upper()}", headers=headers).status_code == 403
    assert client.get(f"/api/users/{str(student.id).upper()}", headers=headers).status_code == 200


# --- recursos inexistentes ---------------------------------------------------

def test_professor_buscando_usuario_inexistente_recebe_404(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.get(f"/api/users/{uuid4()}", headers=auth_header(teacher))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "USER_NOT_FOUND"
    assert body["message"] == "Usuário não encontrado."
    assert body["success"] is False and body["errors"] == []


def test_aluno_buscando_usuario_inexistente_recebe_403_e_nao_404(client, make_user):
    # não revela se o id existe: para quem não pode ver outras contas, a resposta é sempre 403
    student = make_user(UserRole.STUDENT)

    assert client.get(f"/api/users/{uuid4()}", headers=auth_header(student)).status_code == 403


def test_delete_de_usuario_inexistente_retorna_404(client, make_user, repo):
    teacher = make_user(UserRole.TEACHER)

    response = client.delete(f"/api/users/{uuid4()}", headers=auth_header(teacher))

    assert response.status_code == 404
