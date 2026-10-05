# app/

Código-fonte do backend do ApoiaMais. O backend é **uma aplicação FastAPI** (serviço `api` no `docker-compose.yml`; o contrato OpenAPI se chama `auth-service` em `contratos.json`), organizada em camadas inspiradas em Clean Architecture, mais o processo `app/worker.py` (`api-worker`) e o worker Go em `workers/go-worker`. Visão geral em [`docs/ARQUITETURA.md`](../docs/ARQUITETURA.md).

O ponto de entrada fica fora desta pasta, em [`../main.py`](../main.py), que cria a instância `app` do FastAPI, registra os handlers de exceção, o CORS e os routers.

## Estrutura

```text
app/
├── alembic/                  Migrations do banco (Alembic)
├── alembic.ini               Configuração do Alembic
├── api/                      Camada HTTP: routers, dependências (DI) e handlers de exceção
├── application/              Casos de uso e DTOs (Pydantic)
├── core/                     Configuração da aplicação (Pydantic Settings)
├── domain/                   Entidades, enums, exceções e interfaces (repositórios e serviços)
└── infrastructure/           SQLAlchemy (models, sessão, repositórios) e segurança (JWT, hash de senha)
```

Cada pasta tem um README próprio com o detalhamento:

- [`api/README.md`](api/README.md)
- [`application/README.md`](application/README.md)
- [`core/README.md`](core/README.md)
- [`domain/README.md`](domain/README.md)
- [`infrastructure/README.md`](infrastructure/README.md)
- [`alembic/README`](alembic/README)

## Camadas e dependências

```text
            main.py
               │
               ▼
┌──────────────────────────────┐
│ api/                         │  routers, Depends(), exception handlers
└──────┬───────────────┬───────┘
       │               │ (dependencies/ instancia as implementações concretas)
       ▼               ▼
┌──────────────┐   ┌──────────────────────┐
│ application/ │   │ infrastructure/      │  SQLAlchemy, JWT, PBKDF2
└──────┬───────┘   └──────────┬───────────┘
       │                      │ implementa as interfaces do domínio
       ▼                      ▼
┌──────────────────────────────┐
│ domain/                      │  sem dependência de framework
└──────────────────────────────┘
```

| Camada            | Importa de                                   | Responsabilidade |
|-------------------|----------------------------------------------|------------------|
| `api/`            | `application/`, `domain/`, `infrastructure/`, `core/` | Receber a requisição, resolver dependências, chamar o caso de uso |
| `application/`    | `domain/`                                    | Orquestrar regras de negócio e montar os DTOs de resposta |
| `domain/`         | nenhuma camada interna                       | Entidades, enums, exceções e contratos (ABCs) |
| `infrastructure/` | `domain/`                                    | Persistência e segurança |
| `core/`           | nenhuma                                      | Leitura de variáveis de ambiente |

A composição (qual implementação concreta atende cada interface) é feita em `api/dependencies/`, via `Depends` do FastAPI.

## Funcionalidades implementadas

| Domínio        | Estado |
|----------------|--------|
| Usuários (CRUD) | Implementado: casos de uso, repositório SQL e rotas em `/api/users` |
| Autenticação   | Implementado: login com JWT em `/api/auth/login` |
| Pacientes, responsáveis, dados clínicos | Somente models e tabelas; sem casos de uso nem rotas |
| Gamificação (mundos, fases, progresso, conquistas, loja, inventário) | Somente models e tabelas |
| Ilustrações por IA (`ai_image`) | Implementado: `/api/stages/{id}/illustration`, `/api/ai-images/{id}`, worker Go |
| Conteúdo gerado por IA (`ai_content`) | Somente model e tabela |
| Arquivos, notificações, auditoria | Somente models e tabelas |
| Relatórios     | Não implementado (arquivos vazios em `application/use_cases/reports/` e `api/routes/reports.py`) |

Redis é usado no rate limit; RabbitMQ, pelo `api-worker` (outbox e resultados) e pelo go-worker.

## Fluxo de uma requisição

Exemplo: `GET /api/users/` (listar usuários).

1. `main.py` direciona a chamada para o router de `api/routes/users.py`.
2. O FastAPI resolve as dependências:
   - `get_current_teacher` valida o token Bearer e exige a role `teacher`;
   - `get_list_user_usecase` cria a sessão do banco, o `SqlUserRepository` e o `ListUserUseCase`.
3. O caso de uso chama `repository.list()`, que devolve entidades `User` do domínio.
4. O caso de uso converte as entidades em `UserResponse` (DTO) e a rota devolve o JSON.
5. Se uma `DomainException` for lançada, o handler em `api/exception_handlers.py` converte em resposta HTTP.

## Testes

Os testes ficam em [`../tests/`](../tests/README.md), fora desta pasta.
