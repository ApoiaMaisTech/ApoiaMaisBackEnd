"""Matriz de autorização: cada rota x cada perfil, com use cases e rotas reais.

A tabela de referência está no topo de app/api/routes/users.py. Ao criar uma
rota nova, adicione as linhas dela aqui; o teste final falha se faltar.
"""

from uuid import uuid4

import pytest

from main import app

from app.domain.enums.user import UserRole

from tests.integration.api.helpers import auth_header, forge_token

ANON, STUDENT, TEACHER = "anonimo", "aluno", "professor"

# alvos: o próprio ator, outro aluno, outro professor
SELF, OTHER_STUDENT, OTHER_TEACHER = "self", "outro_aluno", "outro_professor"


def _novo_usuario():
    return {"name": "Novo Usuário", "email": f"{uuid4().hex[:8]}@example.com", "password": "senha-nova-123"}


# (método, rota, alvo, ator, status esperado)
MATRIX = [
    ("POST", "/api/users/students", None, ANON, 401),
    ("POST", "/api/users/students", None, STUDENT, 403),
    ("POST", "/api/users/students", None, TEACHER, 201),

    ("POST", "/api/users/teachers", None, ANON, 401),
    ("POST", "/api/users/teachers", None, STUDENT, 403),
    ("POST", "/api/users/teachers", None, TEACHER, 201),

    ("GET", "/api/users/", None, ANON, 401),
    ("GET", "/api/users/", None, STUDENT, 403),
    ("GET", "/api/users/", None, TEACHER, 200),

    ("GET", "/api/users/{id}", OTHER_STUDENT, ANON, 401),
    ("GET", "/api/users/{id}", SELF, STUDENT, 200),
    ("GET", "/api/users/{id}", OTHER_STUDENT, STUDENT, 403),
    ("GET", "/api/users/{id}", OTHER_TEACHER, STUDENT, 403),
    ("GET", "/api/users/{id}", SELF, TEACHER, 200),
    ("GET", "/api/users/{id}", OTHER_STUDENT, TEACHER, 200),
    ("GET", "/api/users/{id}", OTHER_TEACHER, TEACHER, 200),

    ("PUT", "/api/users/{id}", OTHER_STUDENT, ANON, 401),
    ("PUT", "/api/users/{id}", SELF, STUDENT, 200),
    ("PUT", "/api/users/{id}", OTHER_STUDENT, STUDENT, 403),
    ("PUT", "/api/users/{id}", OTHER_TEACHER, STUDENT, 403),
    ("PUT", "/api/users/{id}", SELF, TEACHER, 200),
    ("PUT", "/api/users/{id}", OTHER_STUDENT, TEACHER, 403),
    ("PUT", "/api/users/{id}", OTHER_TEACHER, TEACHER, 403),

    ("DELETE", "/api/users/{id}", OTHER_STUDENT, ANON, 401),
    ("DELETE", "/api/users/{id}", SELF, STUDENT, 403),
    ("DELETE", "/api/users/{id}", OTHER_STUDENT, STUDENT, 403),
    ("DELETE", "/api/users/{id}", OTHER_STUDENT, TEACHER, 204),
    ("DELETE", "/api/users/{id}", OTHER_TEACHER, TEACHER, 403),
    ("DELETE", "/api/users/{id}", SELF, TEACHER, 403),
]


@pytest.mark.parametrize(
    "method,path,target,actor,expected",
    MATRIX,
    ids=[f"{m} {p} alvo={t} ator={a} -> {e}" for m, p, t, a, e in MATRIX],
)
def test_matriz_de_autorizacao(client, make_user, repo, method, path, target, actor, expected):
    users = {
        STUDENT: make_user(UserRole.STUDENT),
        TEACHER: make_user(UserRole.TEACHER),
        OTHER_STUDENT: make_user(UserRole.STUDENT),
        OTHER_TEACHER: make_user(UserRole.TEACHER),
    }
    headers = auth_header(users[actor]) if actor != ANON else {}

    target_user = None
    if target == SELF:
        target_user = users[actor]
    elif target is not None:
        target_user = users[target]

    url = path.replace("{id}", str(target_user.id)) if target_user else path

    body = None
    if method == "POST":
        body = _novo_usuario()
    elif method == "PUT":
        body = {"email": target_user.email, "password": "senha-alterada-123"}

    total_before = len(repo.users)
    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == expected, response.text

    # negado não pode ter efeito colateral
    if expected in (401, 403):
        assert len(repo.users) == total_before
        if target_user is not None:
            assert repo.users[target_user.id].password_hash == target_user.password_hash
        body = response.json()
        assert body["success"] is False
        assert body["message"]
    if expected == 401:
        assert response.headers.get("www-authenticate") == "Bearer"


def test_matriz_cobre_todas_as_rotas_de_usuarios():
    cobertas = {(m, p) for m, p, *_ in MATRIX}
    existentes = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/users")
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
    }
    existentes = {(m, p.replace("{user_id}", "{id}")) for m, p in existentes}
    assert existentes - cobertas == set(), "rota sem linha na matriz de autorização"


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({"Authorization": "Bearer nao-e-um-jwt"}, id="token-malformado"),
        pytest.param({"Authorization": "Basic dXNlcjpwYXNz"}, id="esquema-errado"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "teacher"}, secret="outro-segredo"), id="assinatura-invalida"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "teacher", "exp": 1}), id="expirado"),
        pytest.param(forge_token({"user_id": str(uuid4()), "role": "superuser"}), id="role-desconhecida"),
        pytest.param(forge_token({"user_id": "nao-e-uuid", "role": "teacher"}), id="user-id-invalido"),
        pytest.param(forge_token({"role": "teacher"}), id="sem-user-id"),
    ],
)
def test_tokens_invalidos_retornam_401(client, repo, headers):
    response = client.get("/api/users/", headers=headers)

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_professor_buscando_usuario_inexistente_recebe_404(client, make_user):
    teacher = make_user(UserRole.TEACHER)

    response = client.get(f"/api/users/{uuid4()}", headers=auth_header(teacher))

    assert response.status_code == 404
    assert response.json() == {"success": False, "message": "User not found", "errors": []}


def test_delete_de_usuario_inexistente_retorna_404(client, make_user, repo):
    teacher = make_user(UserRole.TEACHER)

    response = client.delete(f"/api/users/{uuid4()}", headers=auth_header(teacher))

    assert response.status_code == 404
