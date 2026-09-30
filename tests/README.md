# tests/

Testes automatizados do backend, executados com **pytest** e **pytest-asyncio**. A configuração fica em [`../pytest.ini`](../pytest.ini) (`pythonpath = .` e event loop com escopo de sessão).

## Estrutura

```text
tests/
├── unit/
│   └── use_cases/users/test_user_usecases.py      Casos de uso com mocks
└── integration/
    ├── conftest.py                                Fixture db_session (MySQL real)
    ├── api/
    │   ├── test_users.py                          Rotas de /api/users via TestClient
    │   └── test_health.py                         Vazio
    └── repositories/
        ├── test_repository.py                     Criar e buscar usuário
        ├── test_user_repository_crud.py           Listar, atualizar, remover
        ├── test_user_repository_email.py          Busca por e-mail
        └── repositories/
            └── test_user_repository_errors.py     Casos de erro e e-mail duplicado
```

## O que cada grupo cobre

| Grupo | Dependências externas | Cobertura |
|-------|-----------------------|-----------|
| `unit/` | Nenhuma | Criar, buscar, listar, atualizar e remover usuário, incluindo e-mail duplicado e usuário inexistente |
| `integration/api/` | Variáveis de ambiente (`DB_USER`, `DB_NAME`, `JWT_SECRET_KEY`), pois importa `main.py` | Status e corpo das rotas de usuário. Os casos de uso são substituídos por mocks via `app.dependency_overrides` |
| `integration/repositories/` | MySQL com as migrations aplicadas | `SqlUserRepository` contra o banco real |

Ainda não há testes de login, JWT, hash de senha, autorização (401 e 403) nem dos handlers de exceção.

## Como executar

Somente testes unitários (sem banco):

```bash
pytest tests/unit
```

Suíte completa, com um MySQL acessível e as variáveis de ambiente do banco definidas:

```bash
python -m alembic -c app/alembic.ini upgrade head
pytest -v
```

No CI (`.github/workflows/ci.yml`), um MySQL 8.0 sobe como serviço, as migrations são aplicadas e depois o `pytest -v` é executado.

## Isolamento

A fixture `db_session` faz `rollback` ao final, mas o repositório faz `commit` em cada operação. Por isso, os dados criados pelos testes de repositório **permanecem no banco**. Os testes usam e-mails com UUID para não colidir entre execuções. Use um banco dedicado a testes.
